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
