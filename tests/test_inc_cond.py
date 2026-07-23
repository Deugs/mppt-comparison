import pytest

from src import config
from src.algorithms.inc_cond import IncrementalConductance
from tests._helpers import run_tracking, run_tracking_with_irradiance_step, true_mpp_power


def test_finds_mpp_at_stc(pv_model_stc):
    algorithm = IncrementalConductance()
    history = run_tracking(algorithm, pv_model_stc, iterations=500)

    mpp_power = true_mpp_power(pv_model_stc)
    steady_state_powers = [v * i for v, i, _ in history[-50:]]
    mean_power = sum(steady_state_powers) / len(steady_state_powers)

    relative_error = abs(mean_power - mpp_power) / mpp_power
    assert relative_error < config.MPPT_CONVERGENCE_THRESHOLD


def test_reset_clears_history():
    algorithm = IncrementalConductance()
    algorithm.step(30.0, 8.0, 0.3)
    assert algorithm._v_prev is not None

    algorithm.reset()
    assert algorithm._v_prev is None
    assert algorithm._i_prev is None


def test_duty_cycle_stays_within_bounds(pv_model_stc):
    algorithm = IncrementalConductance()
    history = run_tracking(algorithm, pv_model_stc, iterations=200)
    duty_cycles = [d for _, _, d in history]
    assert all(config.MPPT_DUTY_MIN <= d <= config.MPPT_DUTY_MAX for d in duty_cycles)


def test_steady_state_oscillation_is_bounded(pv_model_stc):
    algorithm = IncrementalConductance()
    history = run_tracking(algorithm, pv_model_stc, iterations=500)
    steady_state_powers = [v * i for v, i, _ in history[-50:]]
    power_range = max(steady_state_powers) - min(steady_state_powers)
    mpp_power = true_mpp_power(pv_model_stc)
    assert power_range / mpp_power < 0.02


def test_recovers_from_duty_clamp_when_mpp_later_becomes_reachable(pv_model_stc):
    """Regression test for a real bug found via the paper's peer-review audit
    (CLAUDE.md Phase 2): at 200 W/m^2 the true MPP requires an effective
    source resistance R_in=18.6 Ohm, but a boost converter can only ever
    present R_in = R_load*(1-D)^2 <= R_load = 9.2 Ohm, so this algorithm
    drives duty to MPPT_DUTY_MIN and gets clamped there -- and, uncorrected,
    |dV|~=0 at the clamp reads as "converged," permanently freezing it even
    once irradiance later rises enough that the true MPP becomes reachable.
    """
    algorithm = IncrementalConductance()
    history = run_tracking_with_irradiance_step(
        algorithm,
        pv_model_stc,
        low_irradiance=200.0,
        low_iterations=300,
        high_irradiance=config.STC_IRRADIANCE,
        high_iterations=500,
    )

    mpp_power = true_mpp_power(pv_model_stc, irradiance=config.STC_IRRADIANCE)
    steady_state_powers = [v * i for v, i, _ in history[-50:]]
    mean_power = sum(steady_state_powers) / len(steady_state_powers)

    relative_error = abs(mean_power - mpp_power) / mpp_power
    assert relative_error < config.MPPT_CONVERGENCE_THRESHOLD
