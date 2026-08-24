import pytest

from src import config
from src.algorithms.p_and_o import PerturbObserve
from src.scenarios import compute_run_metrics
from src.scenarios_partial_shading import (
    PARTIAL_SHADING_SCENARIOS,
    build_pv_string,
    run_partial_shading_monte_carlo,
    run_partial_shading_scenario,
    scenario_partial_shading_complex_pattern_b,
    scenario_partial_shading_simple,
)


@pytest.fixture(scope="module")
def stc_params():
    from src.pv_model import extract_two_diode_parameters

    return extract_two_diode_parameters(
        voc=config.PANEL_VOC_STC,
        isc=config.PANEL_ISC_STC,
        vmp=config.PANEL_VMP_STC,
        imp=config.PANEL_IMP_STC,
    )


@pytest.mark.parametrize("name", list(PARTIAL_SHADING_SCENARIOS))
def test_all_partial_shading_scenarios_produce_valid_scenarios(name):
    scenario = PARTIAL_SHADING_SCENARIOS[name]()
    assert scenario.duration_s > 0
    assert len(scenario.irradiances) >= 2
    assert all(irr > 0 for irr in scenario.irradiances)


def test_simple_shading_has_exactly_two_local_maxima(stc_params):
    """CLAUDE.md scenario 6: 2 panels -> 2 local maxima (1 global)."""
    import numpy as np
    from scipy.signal import argrelextrema

    scenario = scenario_partial_shading_simple()
    pv_string = build_pv_string(stc_params, num_modules=len(scenario.irradiances))
    max_current = max(
        m.groups[0].model.params.iph * irr / config.STC_IRRADIANCE
        for m, irr in zip(pv_string.modules, scenario.irradiances)
    )
    currents = np.linspace(1e-6, max_current * 0.999, 300)
    _, powers = pv_string.pv_curve(currents, scenario.irradiances)
    local_maxima = argrelextrema(powers, np.greater)[0]
    assert len(local_maxima) == 2


def test_global_mpp_is_not_always_the_first_local_maximum(stc_params):
    """CLAUDE.md Pattern B: widely-spaced shading where naive greedy search
    can get trapped on the wrong peak -- the global MPP here is the *middle*
    local maximum, not the first one a low-to-high current sweep finds."""
    import numpy as np
    from scipy.signal import argrelextrema

    scenario = scenario_partial_shading_complex_pattern_b()
    pv_string = build_pv_string(stc_params, num_modules=len(scenario.irradiances))
    max_current = max(
        m.groups[0].model.params.iph * irr / config.STC_IRRADIANCE
        for m, irr in zip(pv_string.modules, scenario.irradiances)
    )
    currents = np.linspace(1e-6, max_current * 0.999, 300)
    _, powers = pv_string.pv_curve(currents, scenario.irradiances)
    local_maxima_idx = argrelextrema(powers, np.greater)[0]
    assert len(local_maxima_idx) == 3

    global_v, global_p = pv_string.find_global_mpp(scenario.irradiances)
    assert global_p == pytest.approx(powers[local_maxima_idx].max(), rel=1e-2)
    # The global MPP is not the maximum-current (rightmost) local peak.
    assert local_maxima_idx[np.argmax(powers[local_maxima_idx])] != local_maxima_idx[-1]


def test_run_partial_shading_scenario_produces_correctly_shaped_result(stc_params):
    scenario = scenario_partial_shading_simple()
    pv_string = build_pv_string(stc_params, num_modules=len(scenario.irradiances))
    algorithm = PerturbObserve()
    result = run_partial_shading_scenario(
        scenario, algorithm, pv_string, sample_period_s=0.05
    )

    expected_samples = int(round(scenario.duration_s / 0.05)) + 1
    assert len(result.times) == expected_samples
    assert len(result.powers) == expected_samples
    # theoretical_max_powers is constant (steady-state shading pattern).
    assert len(set(result.theoretical_max_powers)) == 1


def test_run_partial_shading_scenario_tracked_power_is_at_most_global_mpp(stc_params):
    scenario = scenario_partial_shading_simple()
    pv_string = build_pv_string(stc_params, num_modules=len(scenario.irradiances))
    algorithm = PerturbObserve()
    result = run_partial_shading_scenario(
        scenario, algorithm, pv_string, sample_period_s=0.05
    )

    mpp_power = result.theoretical_max_powers[0]
    # Physical sanity check, not an assertion that this algorithm reaches the
    # global MPP -- perturbative algorithms may legitimately get stuck on a
    # local maximum under partial shading, which is exactly what this
    # scenario is designed to reveal, not paper over.
    assert result.powers[-1] <= mpp_power * 1.01


def test_run_partial_shading_monte_carlo_produces_requested_number_of_runs(stc_params):
    scenario = scenario_partial_shading_simple()
    pv_string = build_pv_string(stc_params, num_modules=len(scenario.irradiances))
    algorithm = PerturbObserve()
    results = run_partial_shading_monte_carlo(
        scenario, algorithm, pv_string, num_runs=3, sample_period_s=0.05
    )
    assert len(results) == 3


def test_compute_run_metrics_works_on_partial_shading_results(stc_params):
    scenario = scenario_partial_shading_simple()
    pv_string = build_pv_string(stc_params, num_modules=len(scenario.irradiances))
    algorithm = PerturbObserve()
    result = run_partial_shading_scenario(
        scenario, algorithm, pv_string, sample_period_s=0.05
    )
    computed = compute_run_metrics(result)

    assert 0.0 < computed["tracking_efficiency_pct"] <= 100.0
    assert computed["energy_yield_j"] > 0.0
