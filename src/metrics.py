"""Per-run metric computation (CLAUDE.md "Metrics" section).

All time-series metrics take parallel arrays (times, powers,
theoretical_max_powers) rather than owning scenario execution -- decoupling
"how a run was produced" (scenarios.py) from "what we measure about it"
keeps both independently testable.
"""

import time as time_module

import numpy as np

from . import config


class MetricsCalculator:
    """Convenience class to compute all metrics in one call."""
    
    def __init__(self):
        pass
    
    def compute_all_metrics(
        self,
        power: np.ndarray,
        reference_power: np.ndarray,
        duty_cycle: np.ndarray,
        time: np.ndarray,
        settling_threshold: float = 0.02,
    ) -> dict:
        """Compute all standard MPPT metrics.
        
        Args:
            power: Actual power trajectory
            reference_power: Theoretical maximum power trajectory
            duty_cycle: Duty cycle trajectory
            time: Time array
            settling_threshold: Threshold for settling detection
            
        Returns:
            Dictionary with all computed metrics
        """
        # Tracking efficiency
        tracking_eff = tracking_efficiency(time, power, reference_power)
        
        # Convergence time
        conv_time = convergence_time(time, power, reference_power, threshold=settling_threshold)
        
        # Settling time
        settle_time_val = settling_time(time, power, reference_power, threshold=settling_threshold)
        
        # Steady-state oscillation
        if settle_time_val is not None:
            osc_peak_to_peak, osc_std = steady_state_oscillation(time, power, settle_time_val)
        else:
            osc_peak_to_peak, osc_std = 0.0, 0.0
        
        # Energy yield
        energy = energy_yield(time, power)
        energy_ratio = energy_yield_ratio(time, power, reference_power)
        
        return {
            "tracking_efficiency_pct": tracking_eff,
            "convergence_time_s": conv_time if conv_time is not None else float('nan'),
            "settling_time_s": settle_time_val if settle_time_val is not None else float('nan'),
            "oscillation_peak_to_peak_w": osc_peak_to_peak,
            "oscillation_std_w": osc_std,
            "energy_yield_j": energy,
            "energy_yield_ratio": energy_ratio,
        }


def tracking_efficiency(
    times: np.ndarray, powers: np.ndarray, theoretical_max_powers: np.ndarray
) -> float:
    """eta = integral(P_actual dt) / integral(P_theoretical_max dt) * 100, in percent."""
    actual_energy = np.trapz(powers, times)
    max_energy = np.trapz(theoretical_max_powers, times)
    return actual_energy / max_energy * 100.0


def convergence_time(
    times: np.ndarray,
    powers: np.ndarray,
    theoretical_max_powers: np.ndarray,
    threshold: float = config.MPPT_CONVERGENCE_THRESHOLD,
):
    """First time the tracked power comes within `threshold` of the theoretical max.

    Returns None if the run never converges within the given tolerance.
    """
    relative_error = np.abs(powers - theoretical_max_powers) / theoretical_max_powers
    converged = np.nonzero(relative_error <= threshold)[0]
    return times[converged[0]] if len(converged) else None


def settling_time(
    times: np.ndarray,
    powers: np.ndarray,
    theoretical_max_powers: np.ndarray,
    threshold: float = config.MPPT_CONVERGENCE_THRESHOLD,
    min_duration_s: float = config.SETTLING_WINDOW_S,
):
    """First time after which the tracked power stays within `threshold` of the
    theoretical max continuously for at least `min_duration_s`.

    Returns None if no such window exists (including a trailing within-tolerance
    run that reaches the end of the data without accumulating min_duration_s --
    that can't be confirmed as "settled" from the data available).
    """
    relative_error = np.abs(powers - theoretical_max_powers) / theoretical_max_powers
    within = relative_error <= threshold
    run_start_index = None
    for index in range(len(times)):
        if within[index]:
            if run_start_index is None:
                run_start_index = index
            if times[index] - times[run_start_index] >= min_duration_s:
                return times[run_start_index]
        else:
            run_start_index = None
    return None


def steady_state_oscillation(times: np.ndarray, powers: np.ndarray, settle_time: float):
    """(peak-to-peak, std) of power for samples at or after `settle_time`.

    Returns (0.0, 0.0) if fewer than 2 samples fall in the steady-state window.
    """
    mask = times >= settle_time
    steady_powers = powers[mask]
    if len(steady_powers) < 2:
        return 0.0, 0.0
    return float(steady_powers.max() - steady_powers.min()), float(steady_powers.std())


def energy_yield(times: np.ndarray, powers: np.ndarray) -> float:
    """Total energy extracted over the run, via trapezoidal integration, in Joules (W*s)."""
    return float(np.trapz(powers, times))


def energy_yield_ratio(
    times: np.ndarray, powers: np.ndarray, theoretical_max_powers: np.ndarray
) -> float:
    """E_actual / E_theoretical_max, as a fraction (not percent)."""
    return energy_yield(times, powers) / energy_yield(times, theoretical_max_powers)


def mean_step_execution_time(
    algorithm, v: float, i: float, duty_cycle: float, n_calls: int = 1000
) -> float:
    """Average wall-clock seconds per `algorithm.step()` call, for the
    "execution time per iteration" / computational-burden metrics."""
    start = time_module.perf_counter()
    for _ in range(n_calls):
        algorithm.step(v, i, duty_cycle)
    elapsed = time_module.perf_counter() - start
    return elapsed / n_calls


def relative_computational_burden(step_times: dict, baseline_key: str) -> dict:
    """Each algorithm's mean step time normalized to `baseline_key`'s (e.g. P&O)."""
    baseline = step_times[baseline_key]
    return {name: t / baseline for name, t in step_times.items()}
