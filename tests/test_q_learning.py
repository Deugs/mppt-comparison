import pytest

from src import config
from src.algorithms.q_learning import QLearning, train_q_learning
from tests._helpers import run_tracking, true_mpp_power


@pytest.fixture(scope="module")
def trained_agent(pv_model_stc):
    agent = QLearning()
    train_q_learning(agent, pv_model_stc)
    return agent


def _relative_mpp_error(agent, pv_model, irradiance, iterations=200):
    agent.reset()
    history = run_tracking(
        agent, pv_model, iterations=iterations, irradiance=irradiance
    )
    mpp_power = true_mpp_power(pv_model, irradiance=irradiance)
    steady_state_powers = [v * i for v, i, _ in history[-50:]]
    mean_power = sum(steady_state_powers) / len(steady_state_powers)
    return abs(mean_power - mpp_power) / mpp_power


def test_finds_mpp_at_stc(pv_model_stc, trained_agent):
    assert (
        _relative_mpp_error(trained_agent, pv_model_stc, config.STC_IRRADIANCE)
        < config.MPPT_CONVERGENCE_THRESHOLD
    )


@pytest.mark.parametrize("irradiance", list(config.QL_TRAINING_IRRADIANCES))
def test_finds_mpp_on_training_irradiances(pv_model_stc, trained_agent, irradiance):
    assert (
        _relative_mpp_error(trained_agent, pv_model_stc, irradiance)
        < config.MPPT_CONVERGENCE_THRESHOLD
    )


def test_generalizes_to_held_out_irradiance(pv_model_stc, trained_agent):
    """700 W/m2 is deliberately excluded from QL_TRAINING_IRRADIANCES (config.py)
    so this test can verify the policy generalizes rather than memorizing the
    training conditions -- see CLAUDE.md's Q-learning generalization risk."""
    held_out_irradiance = 700.0
    assert held_out_irradiance not in config.QL_TRAINING_IRRADIANCES
    assert (
        _relative_mpp_error(trained_agent, pv_model_stc, held_out_irradiance)
        < config.MPPT_CONVERGENCE_THRESHOLD
    )


def test_reset_clears_history():
    agent = QLearning()
    agent.step(30.0, 8.0, 0.3)
    assert agent._v_prev is not None

    agent.reset()
    assert agent._v_prev is None
    assert agent._p_prev is None


def test_duty_cycle_stays_within_bounds(pv_model_stc, trained_agent):
    trained_agent.reset()
    history = run_tracking(
        trained_agent, pv_model_stc, iterations=200, irradiance=config.STC_IRRADIANCE
    )
    duty_cycles = [d for _, _, d in history]
    assert all(config.MPPT_DUTY_MIN <= d <= config.MPPT_DUTY_MAX for d in duty_cycles)
