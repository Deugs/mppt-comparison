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


def true_mpp_power(pv_model, irradiance=config.STC_IRRADIANCE, temperature_c=config.STC_TEMPERATURE_C):
    """Reference MPP power, for comparison against tracked power in sanity tests."""
    _, p_mpp = pv_model.find_mpp(irradiance, temperature_c)
    return p_mpp
