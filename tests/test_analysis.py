import numpy as np
import pandas as pd
import pytest

from src import analysis


def _rows(algorithm, scenario, metric, values, ql_condition="not_applicable"):
    return [
        {
            "algorithm": algorithm,
            "scenario": scenario,
            "metric": metric,
            "value": v,
            "run_id": run_id,
            "seed": run_id,
            "ql_condition": ql_condition,
        }
        for run_id, v in enumerate(values)
    ]


def test_summarize_computes_correct_mean_std_ci_and_median_iqr():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    df = pd.DataFrame(
        _rows("p_and_o", "steady_state", "tracking_efficiency_pct", values)
    )

    result = analysis.summarize(df)
    row = result.iloc[0]

    assert row["n"] == 5
    assert row["n_valid"] == 5
    assert row["mean"] == pytest.approx(3.0)
    assert row["std"] == pytest.approx(np.std(values, ddof=1))
    assert row["median"] == pytest.approx(3.0)
    assert row["iqr"] == pytest.approx(
        np.percentile(values, 75) - np.percentile(values, 25)
    )
    # 95% CI must bracket the sample mean and shrink as expected for n=5.
    assert row["ci95_low"] < row["mean"] < row["ci95_high"]


def test_summarize_single_value_group_has_zero_std_and_nan_ci():
    df = pd.DataFrame(
        _rows("p_and_o", "_computational_burden", "mean_step_time_s", [0.001])
    )
    row = analysis.summarize(df).iloc[0]

    assert row["n"] == 1
    assert row["n_valid"] == 1
    assert row["mean"] == pytest.approx(0.001)
    assert row["std"] == 0.0
    assert np.isnan(row["ci95_low"]) and np.isnan(row["ci95_high"])


def test_summarize_convergence_rate_reflects_partial_non_convergence():
    values = [0.05, np.nan, 0.06, np.nan]  # 2 of 4 runs converged
    df = pd.DataFrame(
        _rows("inc_cond", "sensor_noise_robustness", "convergence_time_s", values)
    )

    result = analysis.summarize(df)
    rate_row = result[result["metric"] == "convergence_rate"].iloc[0]
    time_row = result[result["metric"] == "convergence_time_s"].iloc[0]

    assert rate_row["n"] == 4
    assert rate_row["n_valid"] == 2
    assert rate_row["mean"] == pytest.approx(0.5)
    assert (
        0.0 <= rate_row["ci95_low"] <= rate_row["mean"] <= rate_row["ci95_high"] <= 1.0
    )
    # The underlying time metric still summarizes only the converged runs.
    assert time_row["n_valid"] == 2
    assert time_row["mean"] == pytest.approx(0.055)


def test_summarize_convergence_rate_is_explicit_zero_when_nothing_converges():
    """The exact failure mode this function exists to prevent: a group where
    every run failed to converge must show up as an explicit rate of 0.0,
    not silently vanish as an all-NaN mean."""
    values = [np.nan] * 50
    df = pd.DataFrame(
        _rows("p_and_o", "partial_shading_simple", "convergence_time_s", values)
    )

    result = analysis.summarize(df)
    rate_row = result[result["metric"] == "convergence_rate"].iloc[0]
    time_row = result[result["metric"] == "convergence_time_s"].iloc[0]

    assert rate_row["mean"] == 0.0
    assert rate_row["ci95_low"] == pytest.approx(0.0, abs=1e-9)
    assert (
        rate_row["ci95_high"] > 0.0
    )  # Wilson CI is not a degenerate zero-width interval
    assert time_row["n_valid"] == 0
    assert np.isnan(time_row["mean"])


def test_summarize_splits_q_learning_rows_by_ql_condition():
    df = pd.DataFrame(
        _rows(
            "q_learning",
            "steady_state",
            "tracking_efficiency_pct",
            [99.0, 98.0],
            ql_condition="train",
        )
        + _rows(
            "q_learning",
            "temperature_step",
            "tracking_efficiency_pct",
            [80.0, 82.0],
            ql_condition="held_out",
        )
    )
    result = analysis.summarize(df)

    train_row = result[result["ql_condition"] == "train"].iloc[0]
    held_out_row = result[result["ql_condition"] == "held_out"].iloc[0]
    assert train_row["mean"] == pytest.approx(98.5)
    assert held_out_row["mean"] == pytest.approx(81.0)


def test_run_anova_detects_a_real_group_difference():
    df = pd.DataFrame(
        _rows(
            "p_and_o", "steady_state", "oscillation_p2p_w", [1.0, 1.1, 0.9, 1.05, 0.95]
        )
        + _rows(
            "inc_cond", "steady_state", "oscillation_p2p_w", [1.0, 0.9, 1.1, 0.95, 1.05]
        )
        + _rows(
            "sliding_mode",
            "steady_state",
            "oscillation_p2p_w",
            [5.0, 5.1, 4.9, 5.05, 4.95],
        )
    )
    result = analysis.run_anova(
        df,
        "steady_state",
        "oscillation_p2p_w",
        algorithms=("p_and_o", "inc_cond", "sliding_mode"),
    )
    assert result["note"] is None
    assert result["p_value"] < 0.05
    # sliding_mode's group is offset far from the other two -> most of the
    # variance is between-group, so eta-squared should be large (>0.9).
    assert result["eta_squared"] > 0.9


def test_run_anova_eta_squared_is_near_zero_for_identical_groups():
    values = [1.0, 1.1, 0.9, 1.05, 0.95]
    df = pd.DataFrame(
        _rows("p_and_o", "steady_state", "oscillation_p2p_w", values)
        + _rows("inc_cond", "steady_state", "oscillation_p2p_w", values)
    )
    result = analysis.run_anova(
        df, "steady_state", "oscillation_p2p_w", algorithms=("p_and_o", "inc_cond")
    )
    assert result["eta_squared"] == pytest.approx(0.0, abs=1e-9)


def test_run_anova_eta_squared_is_nan_when_every_value_is_identical():
    # Every single value across both groups is the same constant -> ss_total
    # is exactly 0, so eta-squared (a ratio to it) is undefined, not 0.
    df = pd.DataFrame(
        _rows("p_and_o", "steady_state", "oscillation_p2p_w", [1.0, 1.0, 1.0])
        + _rows("inc_cond", "steady_state", "oscillation_p2p_w", [1.0, 1.0, 1.0])
    )
    result = analysis.run_anova(
        df, "steady_state", "oscillation_p2p_w", algorithms=("p_and_o", "inc_cond")
    )
    assert np.isnan(result["eta_squared"])


def test_run_anova_identical_groups_do_not_falsely_reject():
    values = [1.0, 1.1, 0.9, 1.05, 0.95]
    df = pd.DataFrame(
        _rows("p_and_o", "steady_state", "oscillation_p2p_w", values)
        + _rows("inc_cond", "steady_state", "oscillation_p2p_w", values)
    )
    result = analysis.run_anova(
        df, "steady_state", "oscillation_p2p_w", algorithms=("p_and_o", "inc_cond")
    )
    assert result["p_value"] > 0.05


def test_run_anova_flags_insufficient_data():
    df = pd.DataFrame(_rows("p_and_o", "steady_state", "oscillation_p2p_w", [1.0, 1.1]))
    result = analysis.run_anova(
        df, "steady_state", "oscillation_p2p_w", algorithms=("p_and_o", "inc_cond")
    )
    assert result["note"] is not None
    assert np.isnan(result["f_stat"])
    assert np.isnan(result["p_value"])


def test_run_pairwise_ttests_pairs_by_run_id_and_detects_a_shift():
    df = pd.DataFrame(
        _rows(
            "p_and_o",
            "steady_state",
            "tracking_efficiency_pct",
            [99.0, 98.5, 99.2, 98.8, 99.1],
        )
        + _rows(
            "sliding_mode",
            "steady_state",
            "tracking_efficiency_pct",
            [95.0, 94.5, 95.2, 94.8, 95.1],
        )
    )
    results = analysis.run_pairwise_ttests(
        df,
        "steady_state",
        "tracking_efficiency_pct",
        algorithms=("p_and_o", "sliding_mode"),
    )
    assert len(results) == 1
    result = results[0]
    assert result["n_pairs"] == 5
    assert result["p_value"] < 0.05


def test_run_pairwise_ttests_reports_cohens_d_with_sign_matching_t_stat():
    df = pd.DataFrame(
        _rows(
            "p_and_o",
            "steady_state",
            "tracking_efficiency_pct",
            [99.0, 98.5, 99.4, 98.6, 99.3],
        )
        + _rows(
            "sliding_mode",
            "steady_state",
            "tracking_efficiency_pct",
            [95.2, 94.5, 95.0, 94.9, 95.3],
        )
    )
    results = analysis.run_pairwise_ttests(
        df,
        "steady_state",
        "tracking_efficiency_pct",
        algorithms=("p_and_o", "sliding_mode"),
    )
    result = results[0]
    # p_and_o's values are consistently a few points above sliding_mode's
    # (with non-constant per-run differences) -> a large, positive paired
    # effect size, with sign matching the t-statistic.
    assert result["cohens_d"] > 0.8
    assert np.sign(result["cohens_d"]) == np.sign(result["t_stat"])


def test_cohens_d_paired_matches_hand_computed_value():
    a = np.array([2.0, 4.0, 6.0, 8.0])
    b = np.array([1.0, 2.0, 3.0, 4.0])
    diff = a - b  # [1, 2, 3, 4]
    expected = diff.mean() / diff.std(ddof=1)
    assert analysis._cohens_d_paired(a, b) == pytest.approx(expected)


def test_cohens_d_paired_is_nan_for_zero_variance_differences():
    a = np.array([5.0, 6.0, 7.0])
    b = np.array([2.0, 3.0, 4.0])  # constant difference of 3 -> zero variance
    assert np.isnan(analysis._cohens_d_paired(a, b))


def test_run_pairwise_ttests_drops_unpaired_nan_runs():
    df = pd.DataFrame(
        _rows(
            "p_and_o",
            "sensor_noise_robustness",
            "convergence_time_s",
            [0.05, np.nan, 0.06, 0.055],
        )
        + _rows(
            "inc_cond",
            "sensor_noise_robustness",
            "convergence_time_s",
            [0.04, 0.045, np.nan, 0.05],
        )
    )
    results = analysis.run_pairwise_ttests(
        df,
        "sensor_noise_robustness",
        "convergence_time_s",
        algorithms=("p_and_o", "inc_cond"),
    )
    result = results[0]
    # run_id 1 and 2 each have a NaN on one side -- only run_ids 0 and 3 are usable.
    assert result["n_pairs"] == 2


def test_run_pairwise_ttests_reports_missing_algorithm():
    df = pd.DataFrame(
        _rows("p_and_o", "steady_state", "tracking_efficiency_pct", [99.0, 98.0])
    )
    results = analysis.run_pairwise_ttests(
        df,
        "steady_state",
        "tracking_efficiency_pct",
        algorithms=("p_and_o", "q_learning"),
    )
    result = results[0]
    assert result["n_pairs"] == 0
    assert result["note"] is not None


def test_build_full_anova_table_excludes_computational_burden_scenario():
    df = pd.DataFrame(
        _rows("p_and_o", "steady_state", "tracking_efficiency_pct", [99.0, 98.0, 99.5])
        + _rows(
            "inc_cond", "steady_state", "tracking_efficiency_pct", [99.1, 98.1, 99.4]
        )
        + _rows("p_and_o", "_computational_burden", "mean_step_time_s", [0.001])
        + _rows("inc_cond", "_computational_burden", "mean_step_time_s", [0.002])
    )
    result = analysis.build_full_anova_table(df, algorithms=("p_and_o", "inc_cond"))
    assert "_computational_burden" not in set(result["scenario"])
    assert "steady_state" in set(result["scenario"])


def test_fuzzy_sensitivity_table_filters_to_fuzzy_variants():
    df = pd.DataFrame(
        _rows("fuzzy_logic", "steady_state", "tracking_efficiency_pct", [99.0])
        + _rows("fuzzy_5x5", "steady_state", "tracking_efficiency_pct", [98.5])
        + _rows("fuzzy_3x3", "steady_state", "tracking_efficiency_pct", [97.0])
        + _rows("p_and_o", "steady_state", "tracking_efficiency_pct", [99.2])
    )
    summary_df = analysis.summarize(df)
    fuzzy_df = analysis.fuzzy_sensitivity_table(summary_df)
    assert set(fuzzy_df["algorithm"]) == {"fuzzy_logic", "fuzzy_5x5", "fuzzy_3x3"}


def test_holm_bonferroni_matches_classic_worked_example():
    # Classic textbook example (e.g. Holm 1979 / common stats-course
    # worked example): 4 raw p-values, Holm step-down by hand:
    # sorted: 0.01, 0.02, 0.03, 0.04 ; multipliers (m-rank): 4, 3, 2, 1
    # raw products: 0.04, 0.06, 0.06, 0.04 ; step-down running max: 0.04, 0.06, 0.06, 0.06
    p_values = [0.03, 0.01, 0.04, 0.02]
    adjusted = analysis.holm_bonferroni(p_values)
    expected_by_sorted_position = [0.04, 0.06, 0.06, 0.06]
    order = sorted(range(4), key=lambda i: p_values[i])
    for rank, i in enumerate(order):
        assert adjusted[i] == pytest.approx(expected_by_sorted_position[rank])


def test_holm_bonferroni_adjusted_never_smaller_than_raw():
    p_values = [0.001, 0.2, 0.049, 0.5, 0.03]
    adjusted = analysis.holm_bonferroni(p_values)
    for raw, adj in zip(p_values, adjusted):
        assert adj >= raw


def test_holm_bonferroni_preserves_nan_and_excludes_from_family():
    p_values = [0.01, float("nan"), 0.02]
    adjusted = analysis.holm_bonferroni(p_values)
    assert np.isnan(adjusted[1])
    # Family of 2 real tests: multipliers are 2 and 1.
    assert adjusted[0] == pytest.approx(0.02)
    assert adjusted[2] == pytest.approx(0.02)


def test_holm_bonferroni_empty_and_all_nan_input():
    assert analysis.holm_bonferroni([]) == []
    assert all(np.isnan(x) for x in analysis.holm_bonferroni([float("nan")] * 3))


def test_build_full_ttest_table_adds_p_holm_within_each_scenario_metric_family():
    df = pd.DataFrame(
        _rows("p_and_o", "steady_state", "tracking_efficiency_pct", [99.0, 98.5, 99.4, 98.6, 99.3])
        + _rows(
            "inc_cond", "steady_state", "tracking_efficiency_pct", [97.0, 96.5, 97.4, 96.6, 97.3]
        )
        + _rows(
            "fuzzy_logic", "steady_state", "tracking_efficiency_pct", [98.5, 97.9, 98.7, 98.0, 98.6]
        )
    )
    result = analysis.build_full_ttest_table(
        df, algorithms=("p_and_o", "inc_cond", "fuzzy_logic")
    )
    assert "p_holm" in result.columns
    assert result["p_value"].notna().all()  # all 3 pairs have real, distinct data
    # Holm's step-down adjustment can never make a p-value smaller than raw.
    assert (result["p_holm"] >= result["p_value"]).all()
    # With 3 tests in the family, the smallest raw p-value gets multiplied
    # by 3 (Bonferroni-equivalent for the first step of Holm's procedure).
    min_idx = result["p_value"].idxmin()
    assert result.loc[min_idx, "p_holm"] == pytest.approx(
        min(1.0, 3 * result.loc[min_idx, "p_value"])
    )


def test_run_friedman_test_detects_a_real_group_difference():
    df = pd.DataFrame(
        _rows(
            "p_and_o", "steady_state", "oscillation_p2p_w", [1.0, 1.1, 0.9, 1.05, 0.95]
        )
        + _rows(
            "inc_cond", "steady_state", "oscillation_p2p_w", [1.0, 0.9, 1.1, 0.95, 1.05]
        )
        + _rows(
            "sliding_mode",
            "steady_state",
            "oscillation_p2p_w",
            [5.0, 5.1, 4.9, 5.05, 4.95],
        )
    )
    result = analysis.run_friedman_test(
        df,
        "steady_state",
        "oscillation_p2p_w",
        algorithms=("p_and_o", "inc_cond", "sliding_mode"),
    )
    assert result["note"] is None
    assert result["p_value"] < 0.05
    assert result["n_complete_runs"] == 5


def test_run_friedman_test_flags_insufficient_data_below_3_algorithms():
    df = pd.DataFrame(
        _rows("p_and_o", "steady_state", "oscillation_p2p_w", [1.0, 1.1, 0.9])
        + _rows("inc_cond", "steady_state", "oscillation_p2p_w", [1.0, 0.9, 1.1])
    )
    result = analysis.run_friedman_test(
        df, "steady_state", "oscillation_p2p_w", algorithms=("p_and_o", "inc_cond")
    )
    assert result["note"] is not None
    assert np.isnan(result["stat"])
    assert np.isnan(result["p_value"])


def test_run_friedman_test_requires_complete_blocks_across_all_algorithms():
    df = pd.DataFrame(
        _rows(
            "p_and_o", "sensor_noise_robustness", "convergence_time_s", [0.05, np.nan, 0.06]
        )
        + _rows(
            "inc_cond", "sensor_noise_robustness", "convergence_time_s", [0.04, 0.045, 0.05]
        )
        + _rows(
            "sliding_mode",
            "sensor_noise_robustness",
            "convergence_time_s",
            [0.03, 0.035, 0.04],
        )
    )
    result = analysis.run_friedman_test(
        df,
        "sensor_noise_robustness",
        "convergence_time_s",
        algorithms=("p_and_o", "inc_cond", "sliding_mode"),
    )
    # run_id 1 has a NaN for p_and_o -> only run_ids 0 and 2 are complete.
    assert result["n_complete_runs"] == 2


def test_build_full_friedman_table_excludes_computational_burden_scenario():
    df = pd.DataFrame(
        _rows("p_and_o", "steady_state", "tracking_efficiency_pct", [99.0, 98.0, 99.5])
        + _rows(
            "inc_cond", "steady_state", "tracking_efficiency_pct", [99.1, 98.1, 99.4]
        )
        + _rows(
            "fuzzy_logic", "steady_state", "tracking_efficiency_pct", [99.2, 98.2, 99.3]
        )
        + _rows("p_and_o", "_computational_burden", "mean_step_time_s", [0.001])
        + _rows("inc_cond", "_computational_burden", "mean_step_time_s", [0.002])
        + _rows("fuzzy_logic", "_computational_burden", "mean_step_time_s", [0.003])
    )
    result = analysis.build_full_friedman_table(
        df, algorithms=("p_and_o", "inc_cond", "fuzzy_logic")
    )
    assert "_computational_burden" not in set(result["scenario"])
    assert "steady_state" in set(result["scenario"])
