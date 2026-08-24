import pytest

from src import config
from src.algorithms.p_and_o import PerturbObserve
from tests._helpers import run_tracking, true_mpp_power


def test_finds_mpp_at_stc(pv_model_stc):
    algorithm = PerturbObserve()
    history = run_tracking(algorithm, pv_model_stc, iterations=500)

    mpp_power = true_mpp_power(pv_model_stc)
    steady_state_powers = [v * i for v, i, _ in history[-50:]]
    mean_power = sum(steady_state_powers) / len(steady_state_powers)

    relative_error = abs(mean_power - mpp_power) / mpp_power
    assert relative_error < config.MPPT_CONVERGENCE_THRESHOLD


def test_reset_clears_history():
    algorithm = PerturbObserve()
    algorithm.step(30.0, 8.0, 0.3)
    assert algorithm._v_prev is not None

    algorithm.reset()
    assert algorithm._v_prev is None
    assert algorithm._p_prev is None
    assert algorithm._d_prev is None


def test_duty_cycle_stays_within_bounds(pv_model_stc):
    algorithm = PerturbObserve()
    history = run_tracking(algorithm, pv_model_stc, iterations=200)
    duty_cycles = [d for _, _, d in history]
    assert all(config.MPPT_DUTY_MIN <= d <= config.MPPT_DUTY_MAX for d in duty_cycles)
