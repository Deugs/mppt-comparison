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
        "note": None,
    }


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
                "note": None,
            }
        )
    return results


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
    """run_pairwise_ttests() for every (scenario, metric) combination present in `df`."""
    combos = _scenario_metric_combos(df, algorithms, excluded_scenarios)
    rows = []
    for scenario, metric in combos:
        rows.extend(run_pairwise_ttests(df, scenario, metric, algorithms))
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
    fuzzy_df = fuzzy_sensitivity_table(summary_df)

    os.makedirs(args.output, exist_ok=True)
    summary_df.to_csv(os.path.join(args.output, "summary_table.csv"), index=False)
    pd.concat(
        [anova_df.assign(test="anova"), ttest_df.assign(test="paired_ttest")],
        ignore_index=True,
    ).to_csv(os.path.join(args.output, "statistical_tests.csv"), index=False)
    fuzzy_df.to_csv(
        os.path.join(args.output, "fuzzy_sensitivity_table.csv"), index=False
    )

    print(
        f"Wrote {len(summary_df)} summary rows, {len(anova_df)} ANOVA rows, "
        f"{len(ttest_df)} paired-t-test rows, {len(fuzzy_df)} fuzzy-sensitivity rows."
    )


if __name__ == "__main__":
    main()
