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

    Args:
        pv_model: Any object exposing `current_at_voltage` and
            `open_circuit_voltage` (e.g. `pv_model.TwoDiodeModel`).
        duty_cycle: Converter duty cycle, in [0, 1).

    Returns:
        (voltage, current) tuple, in V and A.
    """
    r_in = effective_input_resistance(load_resistance, duty_cycle)

    def residual(v: float) -> float:
        return pv_model.current_at_voltage(v, irradiance, temperature_c) - v / r_in

    voc = pv_model.open_circuit_voltage(irradiance, temperature_c)
    v = brentq(residual, 1e-6, voc * 0.9999, xtol=1e-10, maxiter=200)
    i = pv_model.current_at_voltage(v, irradiance, temperature_c)
    return v, i
