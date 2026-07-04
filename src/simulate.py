"""Steady-state PV/converter operating-point solver.

Treats the boost converter as an ideal, instantaneously-settled DC
transformer rather than simulating its switching transients: for a resistive
load R and duty cycle D, a lossless CCM boost converter presents the PV
source with an effective input resistance

    R_in = R * (1 - D)^2

(from Vin = Vout*(1-D) and Iin = Iout/(1-D) with Vout = Iout*R). The PV
operating point is then the intersection of the panel's I-V curve with the
load line I = V / R_in.

This is the standard simplification for MPPT *algorithm* comparison studies
(this module backs the Phase 2 per-algorithm sanity tests and, later, the
Phase 3 scenario runner) -- it is not a substitute for the transient
state-space model in converter.py, which characterizes the converter itself
rather than the PV-source/converter interaction.
"""

from scipy.optimize import brentq

from . import config


def effective_input_resistance(load_resistance: float, duty_cycle: float) -> float:
    """Ideal lossless boost converter: R_in = R_load * (1 - D)^2."""
    return load_resistance * (1.0 - duty_cycle) ** 2


def pv_operating_point(
    pv_model,
    duty_cycle: float,
    load_resistance: float = config.CONVERTER_LOAD_RESISTANCE,
    irradiance: float = config.STC_IRRADIANCE,
    temperature_c: float = config.STC_TEMPERATURE_C,
):
    """Solve for the (V, I) operating point at a given duty cycle.

    Substitutes the load line V = I*R_in directly into the two-diode
    equation, turning the PV-curve/load-line intersection into a single
    root-find over I rather than an outer voltage search that calls
    `current_at_voltage` (itself a root-find) at every trial point. That
    nested formulation is ~10x slower and matters here: Monte Carlo scenario
    runs and Q-learning training call this thousands of times.

    Args:
        pv_model: A `pv_model.TwoDiodeModel` (needs `.params.iph` and
            `.equation_residual`).
        duty_cycle: Converter duty cycle, in [0, 1).

    Returns:
        (voltage, current) tuple, in V and A.
    """
    r_in = effective_input_resistance(load_resistance, duty_cycle)
    iph = pv_model.params.iph * irradiance / config.STC_IRRADIANCE

    def residual(i: float) -> float:
        return pv_model.equation_residual(i, i * r_in, irradiance, temperature_c)

    i = brentq(residual, -1e-3, iph * 1.01, xtol=1e-9, maxiter=100)
    return i * r_in, i
