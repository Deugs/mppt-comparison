import numpy as np
import pytest

from src import metrics


def test_tracking_efficiency_is_100_percent_at_perfect_tracking():
    times = np.linspace(0, 1, 100)
    max_powers = np.full(100, 250.0)
    powers = max_powers.copy()
    assert metrics.tracking_efficiency(times, powers, max_powers) == pytest.approx(
        100.0
    )


def test_tracking_efficiency_is_50_percent_at_half_power():
    times = np.linspace(0, 1, 100)
    max_powers = np.full(100, 250.0)
    powers = np.full(100, 125.0)
    assert metrics.tracking_efficiency(times, powers, max_powers) == pytest.approx(50.0)


def test_convergence_time_finds_first_within_tolerance_sample():
    times = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    max_powers = np.full(5, 100.0)
    # Only samples at t=0.2 onward are within 2% of 100.
    powers = np.array([50.0, 80.0, 99.0, 99.5, 100.0])
    assert metrics.convergence_time(times, powers, max_powers) == pytest.approx(0.2)


def test_convergence_time_returns_none_if_never_converges():
    times = np.array([0.0, 0.1, 0.2])
    max_powers = np.full(3, 100.0)
    powers = np.array([50.0, 60.0, 70.0])
    assert metrics.convergence_time(times, powers, max_powers) is None


def test_settling_time_requires_full_duration_within_tolerance():
    # Samples every 10ms; power is within 2% of 100 from t=0.02s onward and
    # stays there through the end (t=0.2s) -- 180ms of settled time, >= 100ms.
    times = np.arange(0, 0.21, 0.01)
    max_powers = np.full(len(times), 100.0)
    powers = np.where(times >= 0.02, 100.0, 50.0)
    result = metrics.settling_time(times, powers, max_powers, min_duration_s=0.1)
    assert result == pytest.approx(0.02)


def test_settling_time_rejects_a_dip_that_resets_the_window():
    # Within tolerance for 8 samples (80ms, short of the 100ms requirement),
    # then one sample knocked out of tolerance, repeated -- no continuous run
    # ever reaches min_duration_s, so settling never gets confirmed.
    times = np.arange(0, 0.5, 0.01)
    max_powers = np.full(len(times), 100.0)
    powers = np.full(len(times), 100.0)
    powers[8::9] = 50.0  # break the run every 9th sample
    result = metrics.settling_time(times, powers, max_powers, min_duration_s=0.1)
    assert result is None


def test_settling_time_none_if_within_tolerance_run_too_short():
    times = np.arange(0, 0.05, 0.01)
    max_powers = np.full(len(times), 100.0)
    powers = np.full(
        len(times), 100.0
    )  # settled immediately, but run is only 40ms long
    result = metrics.settling_time(times, powers, max_powers, min_duration_s=0.1)
    assert result is None


def test_steady_state_oscillation_zero_for_constant_power():
    times = np.linspace(0, 1, 100)
    powers = np.full(100, 249.83)
    p2p, std = metrics.steady_state_oscillation(times, powers, settle_time=0.5)
    assert p2p == pytest.approx(0.0)
    assert std == pytest.approx(0.0)


def test_steady_state_oscillation_measures_ripple_after_settle_time():
    times = np.linspace(0, 1, 101)
    powers = np.where(times < 0.5, 0.0, 249.0 + np.sin(times * 100))
    p2p, std = metrics.steady_state_oscillation(times, powers, settle_time=0.5)
    steady = powers[times >= 0.5]
    assert p2p == pytest.approx(steady.max() - steady.min())
    assert std == pytest.approx(steady.std())


def test_energy_yield_matches_trapezoidal_integral_of_constant_power():
    times = np.linspace(0, 10, 1000)
    powers = np.full(1000, 250.0)
    assert metrics.energy_yield(times, powers) == pytest.approx(2500.0, rel=1e-3)


def test_energy_yield_ratio_is_one_at_perfect_tracking():
    times = np.linspace(0, 1, 100)
    max_powers = np.full(100, 250.0)
    assert metrics.energy_yield_ratio(times, max_powers, max_powers) == pytest.approx(
        1.0
    )


def test_mean_step_execution_time_is_positive():
    class DummyAlgorithm:
        def step(self, v, i, duty_cycle):
            return duty_cycle

    dt = metrics.mean_step_execution_time(DummyAlgorithm(), 30.0, 8.0, 0.3, n_calls=100)
    assert dt > 0.0


def test_relative_computational_burden_normalizes_to_baseline():
    step_times = {"p_and_o": 0.001, "fuzzy": 0.004, "q_learning": 0.0005}
    burden = metrics.relative_computational_burden(step_times, baseline_key="p_and_o")
    assert burden["p_and_o"] == pytest.approx(1.0)
    assert burden["fuzzy"] == pytest.approx(4.0)
    assert burden["q_learning"] == pytest.approx(0.5)
