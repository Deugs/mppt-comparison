import numpy as np
import pytest

from src import config, scenarios
from src.algorithms.p_and_o import PerturbObserve


def test_piecewise_constant_holds_value_until_next_breakpoint():
    fn = scenarios.piecewise_constant([(0.0, 1000.0), (1.0, 600.0), (3.0, 1000.0)])
    assert fn(0.0) == 1000.0
    assert fn(0.999) == 1000.0
    assert fn(1.0) == 600.0
    assert fn(2.5) == 600.0
    assert fn(3.0) == 1000.0
    assert fn(4.5) == 1000.0


def test_piecewise_linear_interpolates_between_points():
    fn = scenarios.piecewise_linear([(0.0, 1000.0), (2.0, 600.0)])
    assert fn(0.0) == pytest.approx(1000.0)
    assert fn(1.0) == pytest.approx(800.0)
    assert fn(2.0) == pytest.approx(600.0)


@pytest.mark.parametrize("name", list(scenarios.SINGLE_MODULE_SCENARIOS))
def test_all_scenario_factories_produce_valid_scenarios(name):
    scenario = scenarios.SINGLE_MODULE_SCENARIOS[name]()
    assert scenario.duration_s > 0
    assert scenario.irradiance_fn(0.0) > 0
    assert scenario.temperature_fn(0.0) is not None


def test_run_scenario_produces_correctly_shaped_result(pv_model_stc):
    scenario = scenarios.scenario_steady_state()
    algorithm = PerturbObserve()
    result = scenarios.run_scenario(
        scenario, algorithm, pv_model_stc, sample_period_s=0.01
    )

    expected_samples = int(round(scenario.duration_s / 0.01)) + 1
    assert len(result.times) == expected_samples
    assert len(result.voltages) == expected_samples
    assert len(result.currents) == expected_samples
    assert len(result.powers) == expected_samples
    assert len(result.theoretical_max_powers) == expected_samples
    assert len(result.duty_cycles) == expected_samples
    assert result.times[0] == 0.0
    assert result.times[-1] == pytest.approx(scenario.duration_s)


def test_run_scenario_tracks_mpp_by_end_of_steady_state(pv_model_stc):
    scenario = scenarios.scenario_steady_state()
    algorithm = PerturbObserve()
    result = scenarios.run_scenario(
        scenario, algorithm, pv_model_stc, sample_period_s=0.01
    )

    final_power = result.powers[-1]
    mpp_power = result.theoretical_max_powers[-1]
    assert abs(final_power - mpp_power) / mpp_power < config.MPPT_CONVERGENCE_THRESHOLD


def test_reference_mpp_curve_caches_piecewise_constant_scenario(pv_model_stc):
    scenario = scenarios.scenario_step_change_irradiance()
    times = np.arange(0, scenario.duration_s, 0.01)
    curve = scenarios.reference_mpp_curve(
        pv_model_stc, times, scenario.irradiance_fn, scenario.temperature_fn
    )

    # Distinct irradiance levels (1000, 600, 1000) should give exactly 2
    # distinct theoretical MPP values, not one per sample.
    assert len(set(np.round(curve, 6))) == 2


def test_run_scenario_reflects_irradiance_step_in_theoretical_max(pv_model_stc):
    scenario = scenarios.scenario_step_change_irradiance()
    algorithm = PerturbObserve()
    result = scenarios.run_scenario(
        scenario, algorithm, pv_model_stc, sample_period_s=0.01
    )

    idx_before_step = int(0.9 / 0.01)
    idx_after_step = int(1.5 / 0.01)
    assert (
        result.theoretical_max_powers[idx_before_step]
        > result.theoretical_max_powers[idx_after_step]
    )


def test_sensor_noise_perturbs_algorithm_decisions(pv_model_stc):
    scenario = scenarios.scenario_sensor_noise_robustness()
    import random

    quiet_algorithm = PerturbObserve()
    noisy_algorithm = PerturbObserve()

    quiet_result = scenarios.run_scenario(
        scenario,
        quiet_algorithm,
        pv_model_stc,
        sample_period_s=0.01,
        rng=random.Random(0),
    )
    noisy_scenario = scenarios.Scenario(
        name="loud_noise",
        duration_s=scenario.duration_s,
        irradiance_fn=scenario.irradiance_fn,
        temperature_fn=scenario.temperature_fn,
        sensor_noise_std_frac=0.5,  # exaggerated, to guarantee a detectable difference
    )
    noisy_result = scenarios.run_scenario(
        noisy_scenario,
        noisy_algorithm,
        pv_model_stc,
        sample_period_s=0.01,
        rng=random.Random(0),
    )

    assert not np.array_equal(quiet_result.duty_cycles, noisy_result.duty_cycles)


def test_run_monte_carlo_produces_requested_number_of_runs(pv_model_stc):
    scenario = scenarios.scenario_steady_state()
    algorithm = PerturbObserve()
    results = scenarios.run_monte_carlo(
        scenario, algorithm, pv_model_stc, num_runs=5, sample_period_s=0.02
    )
    assert len(results) == 5


def test_run_monte_carlo_is_reproducible_given_same_seed(pv_model_stc):
    scenario = scenarios.scenario_steady_state()

    results_a = scenarios.run_monte_carlo(
        scenario,
        PerturbObserve(),
        pv_model_stc,
        num_runs=3,
        base_seed=42,
        sample_period_s=0.02,
    )
    results_b = scenarios.run_monte_carlo(
        scenario,
        PerturbObserve(),
        pv_model_stc,
        num_runs=3,
        base_seed=42,
        sample_period_s=0.02,
    )

    for a, b in zip(results_a, results_b):
        assert np.array_equal(a.duty_cycles, b.duty_cycles)


def test_run_monte_carlo_uses_identical_seeds_across_algorithms(pv_model_stc):
    """CLAUDE.md: 'use identical random seeds for fair comparison' -- run k's
    initial duty cycle must be the same regardless of which algorithm runs."""
    scenario = scenarios.scenario_steady_state()

    po_results = scenarios.run_monte_carlo(
        scenario,
        PerturbObserve(),
        pv_model_stc,
        num_runs=3,
        base_seed=7,
        sample_period_s=0.02,
    )
    po_results_again = scenarios.run_monte_carlo(
        scenario,
        PerturbObserve(),
        pv_model_stc,
        num_runs=3,
        base_seed=7,
        sample_period_s=0.02,
    )
    for a, b in zip(po_results, po_results_again):
        assert a.duty_cycles[0] == b.duty_cycles[0]


def test_compute_run_metrics_returns_sane_values(pv_model_stc):
    scenario = scenarios.scenario_steady_state()
    algorithm = PerturbObserve()
    result = scenarios.run_scenario(
        scenario, algorithm, pv_model_stc, sample_period_s=0.01
    )
    computed = scenarios.compute_run_metrics(result)

    assert 0.0 < computed["tracking_efficiency_pct"] <= 100.0
    assert computed["convergence_time_s"] is not None
    assert computed["energy_yield_j"] > 0.0
    assert 0.0 < computed["energy_yield_ratio"] <= 1.0
    assert computed["oscillation_p2p_w"] >= 0.0
    assert computed["oscillation_std_w"] >= 0.0


def test_results_to_rows_has_one_row_per_run_per_metric(pv_model_stc):
    scenario = scenarios.scenario_steady_state()
    results = scenarios.run_monte_carlo(
        scenario, PerturbObserve(), pv_model_stc, num_runs=3, sample_period_s=0.02
    )
    rows = scenarios.results_to_rows("p_and_o", "steady_state", results, base_seed=10)

    num_metrics = len(scenarios.compute_run_metrics(results[0]))
    assert len(rows) == 3 * num_metrics
    assert {r["run_id"] for r in rows} == {0, 1, 2}
    assert {r["seed"] for r in rows} == {10, 11, 12}
    assert all(
        r["algorithm"] == "p_and_o" and r["scenario"] == "steady_state" for r in rows
    )


def test_results_to_rows_forces_ql_condition_to_not_applicable_for_non_q_learning(
    pv_model_stc,
):
    scenario = scenarios.scenario_multi_level_irradiance()
    results = scenarios.run_monte_carlo(
        scenario, PerturbObserve(), pv_model_stc, num_runs=1, sample_period_s=0.02
    )
    rows = scenarios.results_to_rows(
        "p_and_o", "multi_level_irradiance", results, ql_condition="held_out"
    )
    assert all(r["ql_condition"] == "not_applicable" for r in rows)


def test_results_to_rows_keeps_ql_condition_for_q_learning(pv_model_stc):
    scenario = scenarios.scenario_steady_state()
    results = scenarios.run_monte_carlo(
        scenario, PerturbObserve(), pv_model_stc, num_runs=1, sample_period_s=0.02
    )
    rows = scenarios.results_to_rows(
        "q_learning", "steady_state", results, ql_condition="train"
    )
    assert all(r["ql_condition"] == "train" for r in rows)


def test_computational_burden_rows_ql_condition_always_not_applicable():
    step_times = {"p_and_o": 0.001, "q_learning": 0.002}
    rows = scenarios.computational_burden_rows(step_times, baseline_key="p_and_o")
    assert all(r["ql_condition"] == "not_applicable" for r in rows)


@pytest.mark.parametrize(
    "scenario_name,expected",
    [
        ("steady_state", "train"),
        ("step_change_irradiance", "train"),
        ("multi_level_irradiance", "held_out"),
        ("rapid_double_step", "held_out"),
        ("temperature_step", "held_out"),
        ("rapid_fluctuation_cloud_passage", "held_out"),
        ("sensor_noise_robustness", "held_out"),
    ],
)
def test_scenario_ql_condition_classifies_single_module_scenarios(
    scenario_name, expected
):
    scenario = scenarios.SINGLE_MODULE_SCENARIOS[scenario_name]()
    assert scenarios.scenario_ql_condition(scenario) == expected


def test_classify_ql_condition_partial_shading_always_held_out():
    # Even irradiances entirely within QL_TRAINING_IRRADIANCES don't help --
    # Q-learning was never trained on a multi-module string at all.
    assert (
        scenarios.classify_ql_condition(
            irradiances=list(config.QL_TRAINING_IRRADIANCES),
            temperatures_c=[config.STC_TEMPERATURE_C],
            is_partial_shading=True,
        )
        == "held_out"
    )


def test_classify_ql_condition_sensor_noise_is_held_out():
    assert (
        scenarios.classify_ql_condition(
            irradiances=[config.STC_IRRADIANCE],
            temperatures_c=[config.STC_TEMPERATURE_C],
            has_sensor_noise=True,
        )
        == "held_out"
    )


def test_computational_burden_rows_normalizes_to_baseline():
    step_times = {"p_and_o": 0.001, "fuzzy_logic": 0.004}
    rows = scenarios.computational_burden_rows(step_times, baseline_key="p_and_o")

    burden_rows = {
        r["algorithm"]: r["value"] for r in rows if r["metric"] == "relative_burden"
    }
    assert burden_rows["p_and_o"] == pytest.approx(1.0)
    assert burden_rows["fuzzy_logic"] == pytest.approx(4.0)

    time_rows = {
        r["algorithm"]: r["value"] for r in rows if r["metric"] == "mean_step_time_s"
    }
    assert time_rows["p_and_o"] == pytest.approx(0.001)


def test_run_full_sweep_produces_expected_columns_and_algorithms(pv_model_stc):
    """Small-scale smoke test of the full-sweep orchestration -- not the real
    50-run sweep, just verifying the plumbing (algorithm x scenario x
    partial-shading x computational-burden rows) assembles correctly."""
    from src.algorithms.p_and_o import PerturbObserve
    from src.pv_model import extract_two_diode_parameters

    params = extract_two_diode_parameters(
        voc=config.PANEL_VOC_STC,
        isc=config.PANEL_ISC_STC,
        vmp=config.PANEL_VMP_STC,
        imp=config.PANEL_IMP_STC,
    )
    algorithms = {"p_and_o": PerturbObserve()}
    df = scenarios.run_full_sweep(
        algorithms, pv_model_stc, params, num_runs=1, log=lambda msg: None
    )

    assert set(df.columns) == {
        "algorithm",
        "scenario",
        "metric",
        "value",
        "run_id",
        "seed",
        "ql_condition",
    }
    assert set(df["algorithm"]) == {"p_and_o"}
    expected_scenarios = set(scenarios.SINGLE_MODULE_SCENARIOS) | {
        "_computational_burden"
    }
    from src.scenarios_partial_shading import PARTIAL_SHADING_SCENARIOS

    expected_scenarios |= set(PARTIAL_SHADING_SCENARIOS)
    assert set(df["scenario"]) == expected_scenarios


def test_run_full_sweep_skips_computational_burden_when_baseline_absent(pv_model_stc):
    """A fuzzy-variants-only sweep has no "p_and_o" entry to normalize
    against -- must skip the computational-burden step rather than KeyError
    (regression test: this crashed the real fuzzy_5x5/fuzzy_3x3 sweep after
    ~35 minutes of otherwise-successful Monte Carlo runs)."""
    from src.algorithms.fuzzy_logic import FIVE_LABELS, FuzzyLogicController
    from src.pv_model import extract_two_diode_parameters

    params = extract_two_diode_parameters(
        voc=config.PANEL_VOC_STC,
        isc=config.PANEL_ISC_STC,
        vmp=config.PANEL_VMP_STC,
        imp=config.PANEL_IMP_STC,
    )
    algorithms = {"fuzzy_5x5": FuzzyLogicController(labels=FIVE_LABELS)}
    df = scenarios.run_full_sweep(
        algorithms, pv_model_stc, params, num_runs=1, log=lambda msg: None
    )

    assert "_computational_burden" not in set(df["scenario"])
    assert set(df["algorithm"]) == {"fuzzy_5x5"}
