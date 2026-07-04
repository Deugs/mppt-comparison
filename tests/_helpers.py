"""Shared helpers for per-algorithm MPP-finding sanity tests (Phase 2)."""

from src import config
from src.simulate import pv_operating_point


def run_tracking(algorithm, pv_model, iterations=500, initial_duty=0.3, **operating_point_kwargs):
    """Run `algorithm` against `pv_model` for `iterations` steps.

    Returns the list of (voltage, current, duty_cycle) tuples observed at
    each step, in order. `operating_point_kwargs` are forwarded to
    `pv_operating_point` (irradiance, temperature_c, load_resistance).
    """
    duty_cycle = initial_duty
    history = []
    for _ in range(iterations):
        v, i = pv_operating_point(pv_model, duty_cycle, **operating_point_kwargs)
        history.append((v, i, duty_cycle))
        duty_cycle = algorithm.step(v, i, duty_cycle)
    return history


def true_mpp_power(pv_model, irradiance=config.STC_IRRADIANCE, temperature_c=config.STC_TEMPERATURE_C, num_points=2000):
    """Reference MPP power found by a dense voltage sweep, for comparison."""
    voc = pv_model.open_circuit_voltage(irradiance, temperature_c)
    voltages = [voc * (k + 1) / (num_points + 1) for k in range(num_points)]
    powers = [pv_model.power_at_voltage(v, irradiance, temperature_c) for v in voltages]
    return max(powers)
