import pytest

from src import config
from src.algorithms.sliding_mode import SlidingModeControl
from tests._helpers import run_tracking, true_mpp_power


def test_finds_mpp_at_stc(pv_model_stc):
    algorithm = SlidingModeControl()
    history = run_tracking(algorithm, pv_model_stc, iterations=500)

    mpp_power = true_mpp_power(pv_model_stc)
    steady_state_powers = [v * i for v, i, _ in history[-50:]]
    mean_power = sum(steady_state_powers) / len(steady_state_powers)

    relative_error = abs(mean_power - mpp_power) / mpp_power
    assert relative_error < config.MPPT_CONVERGENCE_THRESHOLD


def test_no_sustained_chattering_at_steady_state(pv_model_stc):
    algorithm = SlidingModeControl()
    history = run_tracking(algorithm, pv_model_stc, iterations=500)

    steady_state_powers = [v * i for v, i, _ in history[-50:]]
    mpp_power = true_mpp_power(pv_model_stc)
    power_ripple = max(steady_state_powers) - min(steady_state_powers)
    assert power_ripple / mpp_power < 0.02


def test_boundary_layer_reduces_chattering_vs_narrow_boundary(pv_model_stc):
    """Shrinking the boundary layer toward a pure sign() switching function
    should reproduce the classic SMC chattering problem -- validating that
    config.SMC_BOUNDARY is actually doing the mitigation job it's there for."""
    wide = SlidingModeControl(boundary=0.1)
    narrow = SlidingModeControl(boundary=0.001)

    wide_history = run_tracking(wide, pv_model_stc, iterations=500)
    narrow_history = run_tracking(narrow, pv_model_stc, iterations=500)

    wide_powers = [v * i for v, i, _ in wide_history[-50:]]
    narrow_powers = [v * i for v, i, _ in narrow_history[-50:]]

    wide_ripple = max(wide_powers) - min(wide_powers)
    narrow_ripple = max(narrow_powers) - min(narrow_powers)

    assert narrow_ripple > wide_ripple


def test_reset_clears_history():
    algorithm = SlidingModeControl()
    algorithm.step(30.0, 8.0, 0.3)
    assert algorithm._v_prev is not None

    algorithm.reset()
    assert algorithm._v_prev is None
    assert algorithm._p_prev is None


def test_duty_cycle_stays_within_bounds(pv_model_stc):
    algorithm = SlidingModeControl()
    history = run_tracking(algorithm, pv_model_stc, iterations=300)
    duty_cycles = [d for _, _, d in history]
    assert all(config.MPPT_DUTY_MIN <= d <= config.MPPT_DUTY_MAX for d in duty_cycles)
