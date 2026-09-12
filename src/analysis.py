"""Statistical analysis over the long-format Monte Carlo results table
(CLAUDE.md "Statistical Reporting" / Phase 4 requirements).

`scenarios.results_to_rows()` produces rows with columns:
algorithm, scenario, metric, value, run_id, seed, ql_condition.

This module turns that raw table into:
  - `summarize()`: per (algorithm, scenario, metric[, ql_condition])
    descriptive stats -- mean, std, 95% CI, median, IQR -- over non-NaN
    values, with an explicit n/n_valid so non-convergence isn't silently
    absorbed into a NaN mean.
  - `run_anova()` / `run_pairwise_ttests()`: CLAUDE.md's "ANOVA or paired
    t-test for statistical comparison between algorithms" requirement.
  - `run_friedman_test()`: a rank-based repeated-measures companion to
    run_anova(). The Monte Carlo design already pairs runs across algorithms
    by identical seed (run_id) -- run_anova()'s one-way ANOVA treats the 5
    algorithm groups as independent samples and so ignores that pairing,
    while Friedman uses it directly (same logic run_pairwise_ttests()
    already relies on for its pairing) and, being rank-based, doesn't need
    the normality assumption run_anova()'s F-test does.
  - `run_anova()` also reports eta-squared (SS_between/SS_total) and
    `run_pairwise_ttests()` reports paired Cohen's d, since a p-value alone
    doesn't say whether a statistically-detected difference is large enough
    to matter -- exactly the kind of thing a reviewer asks for once a
    comparison spans hundreds of tests.
  - `holm_bonferroni()`: applied to each (scenario, metric)'s family of
    pairwise t-tests (the natural post-hoc family following one ANOVA) so
    that running ~10 pairwise comparisons per metric doesn't inflate the
    family-wise false-positive rate -- added as a `p_holm` column alongside
    the raw `p_value`, not a replacement for it.

Non-convergence handling (see CLAUDE.md's Q-learning/partial-shading Known
Risks): `convergence_time_s`/`settling_time_s` are NaN whenever a run never
gets within CLAUDE.md's 2% MPP threshold. Several algorithm x scenario pairs
in the actual data are 100% non-convergent (e.g. every perturbative
algorithm under partial shading -- expected, since a unimodal search gets
stuck on a local maximum, exactly what Scenario 6/7 were designed to
surface). A plain `nanmean` over such a group returns NaN and looks like
"no data" rather than "total, informative failure" -- so `summarize()`
additionally emits a `<metric>_rate` row (fraction of runs that converged/
settled, with a Wilson-score 95% CI) computed *before* any NaN-dropping.

Note for whoever reads statistical_tests.csv next: the same near-constant
metric groups that trigger scipy's ConstantInputWarning/precision-loss
warnings in run_anova()/run_pairwise_ttests() (see CLAUDE.md's Phase 4
notes) show up here too, in two new ways worth knowing about rather than
"fixing" by capping -- doing so would just hide the same signal those
warnings already surface. (1) `cohens_d` divides by the *standard
deviation of the paired differences*, not the values themselves, so two
algorithms that agree almost exactly every run (a near-zero but nonzero
diff std) can produce an enormous `cohens_d` that isn't a real large
effect -- always check it alongside `p_value`/`p_holm` and the underlying
`summary_table.csv` std, not in isolation. (2) `run_friedman_test()` is
rank-based and doesn't hit the F-test/t-test precision-loss warning, but
it has its own degenerate case: when every algorithm ties on every single
run (zero rank variance across the whole block), scipy's tie-correction
factor is exactly zero and `stat`/`p_value` come back NaN with a
"RuntimeWarning: invalid value encountered in scalar divide" -- a
genuinely undefined result for a fully-tied block, not a bug.
"""

import itertools

import numpy as np
import pandas as pd
from scipy import stats

# The 5 algorithms spanning CLAUDE.md's 4 MPPT paradigms -- the comparison
# the paper's ANOVA/t-tests are actually about. The fuzzy rule-base variants
# (fuzzy_5x5, fuzzy_3x3) are a within-paradigm ablation, not a competing
# paradigm, so they're compared separately (see fuzzy_sensitivity_table)
# rather than folded into this set by default.
CORE_ALGORITHMS = ("p_and_o", "inc_cond", "fuzzy_logic", "q_learning", "sliding_mode")
FUZZY_VARIANT_ALGORITHMS = ("fuzzy_logic", "fuzzy_5x5", "fuzzy_3x3")

# _computational_burden rows are a single fixed-operating-point measurement
# per algorithm (metrics.mean_step_execution_time) -- n=1, not a Monte Carlo
# distribution, so ANOVA/t-tests over them would be meaningless.
EXCLUDED_SCENARIOS = ("_computational_burden",)

CONVERGENCE_RATE_NAMES = {
    "convergence_time_s": "convergence_rate",
    "settling_time_s": "settling_rate",
}

Z_95 = 1.959963984540054  # stats.norm.ppf(0.975)


def _mean_ci95(values: np.ndarray) -> tuple:
    """95% CI for a mean via Student's t; (nan, nan) if fewer than 2 values."""
    n = len(values)
    if n < 2:
        return float("nan"), float("nan")
    mean = values.mean()
    sem = values.std(ddof=1) / np.sqrt(n)
    half_width = stats.t.ppf(0.975, df=n - 1) * sem
    return mean - half_width, mean + half_width


def _wilson_ci95(successes: int, n: int) -> tuple:
    """Wilson score 95% CI for a proportion successes/n.

    Preferred over the naive normal approximation p +/- 1.96*sqrt(p(1-p)/n)
    because several (algorithm, scenario) groups in the actual data have
    successes=0 (0/50 converged) or successes=n -- the normal approximation
    collapses to a zero-width interval at those extremes (falsely implying
    certainty), while Wilson stays a genuine, bounded interval reflecting
    the sample size.
    """
    if n == 0:
        return float("nan"), float("nan")
    p = successes / n
    z2 = Z_95**2
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half_width = (Z_95 / denom) * np.sqrt(p * (1 - p) / n + z2 / (4 * n**2))
    return max(0.0, center - half_width), min(1.0, center + half_width)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Per (algorithm, scenario, metric[, ql_condition]) descriptive stats.

    For metrics in CONVERGENCE_RATE_NAMES, also emits a derived
    "<metric>_rate" row (n_valid/n with a Wilson 95% CI) alongside the usual
    mean/std/CI/median/IQR-of-the-converged-runs row -- so a group where
    zero runs ever converged shows up as an explicit rate of 0.0, not an
    empty or NaN row that reads as "no data collected."
    """
    group_cols = ["algorithm", "scenario", "metric"]
    if "ql_condition" in df.columns:
        group_cols.append("ql_condition")

    rows = []
    for keys, group in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        key_dict = dict(zip(group_cols, keys))
        values = group["value"].to_numpy(dtype=float)
        n = len(values)
        valid = values[~np.isnan(values)]
        n_valid = len(valid)

        row = dict(key_dict)
        row["n"] = n
        row["n_valid"] = n_valid
        if n_valid > 0:
            ci_low, ci_high = _mean_ci95(valid)
            row["mean"] = valid.mean()
            row["std"] = valid.std(ddof=1) if n_valid > 1 else 0.0
            row["ci95_low"] = ci_low
            row["ci95_high"] = ci_high
            row["median"] = float(np.median(valid))
            row["iqr"] = float(np.percentile(valid, 75) - np.percentile(valid, 25))
        else:
            row["mean"] = row["std"] = row["ci95_low"] = row["ci95_high"] = row[
                "median"
            ] = row["iqr"] = float("nan")
        rows.append(row)

        rate_name = CONVERGENCE_RATE_NAMES.get(key_dict["metric"])
        if rate_name is not None:
            rate_ci_low, rate_ci_high = _wilson_ci95(n_valid, n)
            rate_row = dict(key_dict)
            rate_row["metric"] = rate_name
            rate_row["n"] = n
            rate_row["n_valid"] = n_valid
            rate_row["mean"] = n_valid / n if n > 0 else float("nan")
            rate_row["std"] = float("nan")
            rate_row["ci95_low"] = rate_ci_low
            rate_row["ci95_high"] = rate_ci_high
            rate_row["median"] = float("nan")
            rate_row["iqr"] = float("nan")
            rows.append(rate_row)

    return pd.DataFrame(rows)


def run_anova(
    df: pd.DataFrame, scenario: str, metric: str, algorithms=CORE_ALGORITHMS
) -> dict:
    """One-way ANOVA (scipy.stats.f_oneway) across `algorithms`' per-run
    values for one (scenario, metric), excluding NaN entries within each
    algorithm's group (a non-converged run contributes no convergence_time_s
    sample -- see summarize()'s "<metric>_rate" for that signal instead).

    Returns a dict with f_stat/p_value as NaN and a "note" explaining why if
    fewer than 2 algorithms have >=2 valid values (an F-test needs at least
    2 comparable groups).
    """
    groups = []
    used_algorithms = []
    for algo in algorithms:
        values = (
            df[
                (df.algorithm == algo)
                & (df.scenario == scenario)
                & (df.metric == metric)
            ]["value"]
            .dropna()
            .to_numpy()
        )
        if len(values) >= 2:
            groups.append(values)
            used_algorithms.append(algo)

    if len(groups) < 2:
        return {
            "scenario": scenario,
            "metric": metric,
            "algorithms_used": ",".join(used_algorithms),
            "f_stat": float("nan"),
            "p_value": float("nan"),
            "note": "insufficient data (fewer than 2 algorithms with >=2 valid values)",
        }

    f_stat, p_value = stats.f_oneway(*groups)
    return {
        "scenario": scenario,
        "metric": metric,
        "algorithms_used": ",".join(used_algorithms),
        "f_stat": float(f_stat),
        "p_value": float(p_value),
        "eta_squared": _eta_squared(groups),
        "note": None,
    }


def _eta_squared(groups: list) -> float:
    """SS_between / SS_total for one-way ANOVA -- the fraction of total
    variance explained by algorithm identity. Computed directly from the
    group data (not derived from F) so it doesn't depend on run_anova()'s
    F-statistic being correct."""
    all_values = np.concatenate(groups)
    grand_mean = all_values.mean()
    ss_total = float(np.sum((all_values - grand_mean) ** 2))
    if ss_total == 0.0:
        return float("nan")
    ss_between = float(sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups))
    return ss_between / ss_total


def _cohens_d_paired(a: np.ndarray, b: np.ndarray) -> float:
    """Paired-samples Cohen's d = mean(a - b) / std(a - b, ddof=1).

    Sign convention matches scipy.stats.ttest_rel(a, b)'s t-statistic (both
    are driven by mean(a - b)), so a positive d lines up with a positive
    t_stat. NaN if the differences have zero variance (identical paired
    values -- an undefined but not misleading result, since d is a ratio
    to a standard deviation of zero).
    """
    diff = a - b
    sd = diff.std(ddof=1)
    if sd == 0.0:
        return float("nan")
    return float(diff.mean() / sd)


def holm_bonferroni(p_values) -> list:
    """Holm-Bonferroni step-down adjusted p-values (Holm, 1979) for one
    family of tests, controlling the family-wise error rate less
    conservatively than a flat Bonferroni correction.

    NaN entries (e.g. "insufficient data" tests) are left as NaN and
    excluded from the family for ranking purposes -- they were never
    real tests to correct for.

    Returns adjusted p-values in the same order as the input.
    """
    p_values = list(p_values)
    n = len(p_values)
    valid_idx = [i for i, p in enumerate(p_values) if not (p is None or np.isnan(p))]
    m = len(valid_idx)

    adjusted = [float("nan")] * n
    if m == 0:
        return adjusted

    order = sorted(valid_idx, key=lambda i: p_values[i])
    running_max = 0.0
    for rank, i in enumerate(order):  # rank is 0-indexed
        candidate = (m - rank) * p_values[i]
        running_max = max(running_max, candidate)
        adjusted[i] = min(1.0, running_max)
    return adjusted


def run_pairwise_ttests(
    df: pd.DataFrame, scenario: str, metric: str, algorithms=CORE_ALGORITHMS
) -> list:
    """Paired t-test (scipy.stats.ttest_rel) between every pair of
    `algorithms` for one (scenario, metric), paired by run_id -- valid
    because CLAUDE.md's Monte Carlo design uses identical random seeds
    across algorithms at each run index (scenarios.run_monte_carlo).

    Drops run_ids where either side of a pair is NaN and records how many
    paired observations survived (n_pairs), rather than erroring or
    silently treating missing values as zero.
    """
    sub = df[
        (df.scenario == scenario)
        & (df.metric == metric)
        & (df.algorithm.isin(algorithms))
    ]
    pivot = sub.pivot_table(index="run_id", columns="algorithm", values="value")

    results = []
    for algo_a, algo_b in itertools.combinations(algorithms, 2):
        if algo_a not in pivot.columns or algo_b not in pivot.columns:
            results.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "algorithm_a": algo_a,
                    "algorithm_b": algo_b,
                    "n_pairs": 0,
                    "t_stat": float("nan"),
                    "p_value": float("nan"),
                    "cohens_d": float("nan"),
                    "note": "one or both algorithms missing from this scenario/metric",
                }
            )
            continue

        paired = pivot[[algo_a, algo_b]].dropna()
        n_pairs = len(paired)
        if n_pairs < 2:
            results.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "algorithm_a": algo_a,
                    "algorithm_b": algo_b,
                    "n_pairs": n_pairs,
                    "t_stat": float("nan"),
                    "p_value": float("nan"),
                    "cohens_d": float("nan"),
                    "note": "insufficient paired data (fewer than 2 runs where both converged)",
                }
            )
            continue

        t_stat, p_value = stats.ttest_rel(paired[algo_a], paired[algo_b])
        results.append(
            {
                "scenario": scenario,
                "metric": metric,
                "algorithm_a": algo_a,
                "algorithm_b": algo_b,
                "n_pairs": n_pairs,
                "t_stat": float(t_stat),
                "p_value": float(p_value),
                "cohens_d": _cohens_d_paired(
                    paired[algo_a].to_numpy(), paired[algo_b].to_numpy()
                ),
                "note": None,
            }
        )
    return results


def run_friedman_test(
    df: pd.DataFrame, scenario: str, metric: str, algorithms=CORE_ALGORITHMS
) -> dict:
    """Friedman test (scipy.stats.friedmanchisquare) across `algorithms` for
    one (scenario, metric) -- the rank-based, repeated-measures companion to
    run_anova()'s one-way ANOVA (see module docstring for why: it uses the
    same run_id pairing run_pairwise_ttests() relies on, and is robust to
    the non-normal/near-constant groups that already trigger scipy
    precision-loss warnings elsewhere in this pipeline).

    Requires a complete block: only run_ids where every algorithm in
    `algorithms` has a non-NaN value are used (Friedman is undefined for a
    ragged design). Returns stat/p_value as NaN with a "note" if fewer than
    3 algorithms have complete data or fewer than 2 complete run_ids remain
    (scipy's own minimum for a meaningful rank test).
    """
    sub = df[
        (df.scenario == scenario)
        & (df.metric == metric)
        & (df.algorithm.isin(algorithms))
    ]
    pivot = sub.pivot_table(index="run_id", columns="algorithm", values="value")
    present = [a for a in algorithms if a in pivot.columns]
    complete = pivot[present].dropna()

    if len(present) < 3 or len(complete) < 2:
        return {
            "scenario": scenario,
            "metric": metric,
            "algorithms_used": ",".join(present),
            "n_complete_runs": len(complete),
            "stat": float("nan"),
            "p_value": float("nan"),
            "note": "insufficient data (need >=3 algorithms and >=2 runs complete across all of them)",
        }

    stat, p_value = stats.friedmanchisquare(*[complete[a] for a in present])
    return {
        "scenario": scenario,
        "metric": metric,
        "algorithms_used": ",".join(present),
        "n_complete_runs": len(complete),
        "stat": float(stat),
        "p_value": float(p_value),
        "note": None,
    }


def _scenario_metric_combos(
    df: pd.DataFrame, algorithms, excluded_scenarios=EXCLUDED_SCENARIOS
):
    sub = df[~df.scenario.isin(excluded_scenarios) & df.algorithm.isin(algorithms)]
    return list(
        sub[["scenario", "metric"]].drop_duplicates().itertuples(index=False, name=None)
    )


def build_full_anova_table(
    df: pd.DataFrame, algorithms=CORE_ALGORITHMS, excluded_scenarios=EXCLUDED_SCENARIOS
) -> pd.DataFrame:
    """run_anova() for every (scenario, metric) combination present in `df`."""
    combos = _scenario_metric_combos(df, algorithms, excluded_scenarios)
    rows = [run_anova(df, scenario, metric, algorithms) for scenario, metric in combos]
    return pd.DataFrame(rows)


def build_full_ttest_table(
    df: pd.DataFrame, algorithms=CORE_ALGORITHMS, excluded_scenarios=EXCLUDED_SCENARIOS
) -> pd.DataFrame:
    """run_pairwise_ttests() for every (scenario, metric) combination present
    in `df`, with a Holm-Bonferroni-adjusted `p_holm` column added within
    each (scenario, metric) family -- the up-to-C(len(algorithms), 2)
    pairwise comparisons that would follow one run_anova() call for that
    metric, which is the natural family for a post-hoc correction (see
    holm_bonferroni())."""
    combos = _scenario_metric_combos(df, algorithms, excluded_scenarios)
    rows = []
    for scenario, metric in combos:
        rows.extend(run_pairwise_ttests(df, scenario, metric, algorithms))
    result = pd.DataFrame(rows)
    if not result.empty:
        result["p_holm"] = result.groupby(["scenario", "metric"])["p_value"].transform(
            lambda p: holm_bonferroni(p.to_numpy())
        )
    return result


def build_full_friedman_table(
    df: pd.DataFrame, algorithms=CORE_ALGORITHMS, excluded_scenarios=EXCLUDED_SCENARIOS
) -> pd.DataFrame:
    """run_friedman_test() for every (scenario, metric) combination present in `df`."""
    combos = _scenario_metric_combos(df, algorithms, excluded_scenarios)
    rows = [
        run_friedman_test(df, scenario, metric, algorithms) for scenario, metric in combos
    ]
    return pd.DataFrame(rows)


def fuzzy_sensitivity_table(summary_df: pd.DataFrame) -> pd.DataFrame:
    """The rows of an already-computed summarize() table restricted to the
    7x7/5x5/3x3 fuzzy rule-base variants (CLAUDE.md's fuzzy "Sensitivity
    Analysis (Contribution)" section)."""
    return summary_df[
        summary_df["algorithm"].isin(FUZZY_VARIANT_ALGORITHMS)
    ].reset_index(drop=True)


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Compute statistical summaries over the MPPT comparison results table."
    )
    parser.add_argument("--input", type=str, default="results/comparison_table.csv")
    parser.add_argument("--output", type=str, default="results/")
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    summary_df = summarize(df)
    anova_df = build_full_anova_table(df)
    ttest_df = build_full_ttest_table(df)
    friedman_df = build_full_friedman_table(df)
    fuzzy_df = fuzzy_sensitivity_table(summary_df)

    os.makedirs(args.output, exist_ok=True)
    summary_df.to_csv(os.path.join(args.output, "summary_table.csv"), index=False)
    pd.concat(
        [
            anova_df.assign(test="anova"),
            ttest_df.assign(test="paired_ttest"),
            friedman_df.assign(test="friedman"),
        ],
        ignore_index=True,
    ).to_csv(os.path.join(args.output, "statistical_tests.csv"), index=False)
    fuzzy_df.to_csv(
        os.path.join(args.output, "fuzzy_sensitivity_table.csv"), index=False
    )

    print(
        f"Wrote {len(summary_df)} summary rows, {len(anova_df)} ANOVA rows, "
        f"{len(ttest_df)} paired-t-test rows, {len(friedman_df)} Friedman rows, "
        f"{len(fuzzy_df)} fuzzy-sensitivity rows."
    )


if __name__ == "__main__":
    main()
