import os

import numpy as np
import pandas as pd
import pytest

from src import analysis, plotting
from src.scenarios import RunResult


def _raw_rows(algorithm, scenario, metric, values, ql_condition="not_applicable"):
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


@pytest.fixture
def summary_df():
    rows = []
    scenarios = ["steady_state", "multi_level_irradiance", "partial_shading_simple"]
    non_ql_algorithms = ["p_and_o", "inc_cond", "fuzzy_logic", "sliding_mode"]
    all_algorithms = non_ql_algorithms + ["q_learning"]
    rng = np.random.default_rng(0)
    for scenario in scenarios:
        for algorithm in non_ql_algorithms:
            rows += _raw_rows(
                algorithm,
                scenario,
                "tracking_efficiency_pct",
                rng.uniform(90, 99, size=10).tolist(),
            )
            rows += _raw_rows(
                algorithm,
                scenario,
                "oscillation_p2p_w",
                rng.uniform(0, 2, size=10).tolist(),
            )
            rows += _raw_rows(
                algorithm,
                scenario,
                "energy_yield_ratio",
                rng.uniform(0.9, 0.99, size=10).tolist(),
            )
            convergence_values = [0.05] * 7 + [np.nan] * 3
            rows += _raw_rows(
                algorithm, scenario, "convergence_time_s", convergence_values
            )
            rows += _raw_rows(
                algorithm, scenario, "settling_time_s", convergence_values
            )

    # q_learning: exactly one ql_condition tag per scenario, matching the
    # real pipeline (scenarios.classify_ql_condition tags a whole scenario,
    # never splits one scenario's rows across two conditions).
    ql_condition_by_scenario = {
        "steady_state": "train",
        "multi_level_irradiance": "held_out",
        "partial_shading_simple": "held_out",
    }
    for scenario, condition in ql_condition_by_scenario.items():
        rows += _raw_rows(
            "q_learning",
            scenario,
            "tracking_efficiency_pct",
            rng.uniform(90, 99, size=10).tolist(),
            condition,
        )
        rows += _raw_rows(
            "q_learning",
            scenario,
            "oscillation_p2p_w",
            rng.uniform(0, 2, size=10).tolist(),
            condition,
        )
        rows += _raw_rows(
            "q_learning",
            scenario,
            "energy_yield_ratio",
            rng.uniform(0.9, 0.99, size=10).tolist(),
            condition,
        )
        convergence_values = [0.05] * 7 + [np.nan] * 3
        rows += _raw_rows(
            "q_learning", scenario, "convergence_time_s", convergence_values, condition
        )
        rows += _raw_rows(
            "q_learning", scenario, "settling_time_s", convergence_values, condition
        )

    # computational burden
    for i, algorithm in enumerate(all_algorithms):
        rows += _raw_rows(
            algorithm, "_computational_burden", "mean_step_time_s", [0.001 * (i + 1)]
        )
        rows += _raw_rows(
            algorithm, "_computational_burden", "relative_burden", [float(i + 1)]
        )
    # fuzzy variants
    for fuzzy_algo in ["fuzzy_5x5", "fuzzy_3x3"]:
        rows += _raw_rows(
            fuzzy_algo,
            "steady_state",
            "tracking_efficiency_pct",
            rng.uniform(90, 99, size=10).tolist(),
        )

    df = pd.DataFrame(rows)
    return analysis.summarize(df)


@pytest.fixture
def fuzzy_df(summary_df):
    return analysis.fuzzy_sensitivity_table(summary_df)


def _assert_saved(paths):
    png_path, svg_path = paths
    assert os.path.exists(png_path) and os.path.getsize(png_path) > 0
    assert os.path.exists(svg_path) and os.path.getsize(svg_path) > 0


def test_plot_metric_comparison_saves_png_and_svg(summary_df, tmp_path):
    paths = plotting.plot_metric_comparison(
        summary_df, "tracking_efficiency_pct", str(tmp_path)
    )
    _assert_saved(paths)


def test_plot_convergence_heatmap_saves_png_and_svg(summary_df, tmp_path):
    paths = plotting.plot_convergence_heatmap(summary_df, str(tmp_path))
    _assert_saved(paths)


def test_plot_computational_burden_saves_png_and_svg(summary_df, tmp_path):
    paths = plotting.plot_computational_burden(summary_df, str(tmp_path))
    _assert_saved(paths)


def test_plot_ql_train_vs_held_out_saves_png_and_svg(summary_df, tmp_path):
    paths = plotting.plot_ql_train_vs_held_out(summary_df, str(tmp_path))
    _assert_saved(paths)


def test_plot_fuzzy_sensitivity_saves_png_and_svg(fuzzy_df, tmp_path):
    paths = plotting.plot_fuzzy_sensitivity(fuzzy_df, str(tmp_path))
    _assert_saved(paths)


def test_plot_tracking_trajectory_saves_png_and_svg(tmp_path):
    times = np.linspace(0, 2.0, 50)
    results = {
        "p_and_o": RunResult(
            times=times,
            voltages=np.full(50, 30.0),
            currents=np.full(50, 8.0),
            powers=np.linspace(100, 240, 50),
            theoretical_max_powers=np.full(50, 250.0),
            duty_cycles=np.full(50, 0.4),
        ),
        "sliding_mode": RunResult(
            times=times,
            voltages=np.full(50, 30.0),
            currents=np.full(50, 8.0),
            powers=np.linspace(50, 248, 50),
            theoretical_max_powers=np.full(50, 250.0),
            duty_cycles=np.full(50, 0.4),
        ),
    }
    paths = plotting.plot_tracking_trajectory(
        results, 250.0, str(tmp_path), "trajectory_test", "Test trajectory"
    )
    _assert_saved(paths)


def test_generate_all_aggregate_figures_produces_expected_count(
    summary_df, fuzzy_df, tmp_path
):
    paths = plotting.generate_all_aggregate_figures(summary_df, fuzzy_df, str(tmp_path))
    # 3 metric-comparison + 2 heatmaps + 1 burden + 1 ql-train-vs-held-out + 1 fuzzy-sensitivity
    assert len(paths) == 8
    for png_path, svg_path in paths:
        assert os.path.exists(png_path)
        assert os.path.exists(svg_path)


def test_color_for_is_deterministic_for_unknown_names():
    assert plotting._color_for("some_unknown_algorithm") == plotting._color_for(
        "some_unknown_algorithm"
    )
