"""Boost converter: component sizing, state-space averaged small-signal model,
and continuous/discontinuous conduction mode (CCM/DCM) boundary check.

Sizing citation (mandatory, per CLAUDE.md): Erickson, R.W., and Maksimovic, D.
"Fundamentals of Power Electronics." The 30% inductor-ripple and small-signal
transfer function derivations below follow that text's boost-converter
treatment, including the right-half-plane (RHP) zero in Gvd(s) -- CLAUDE.md's
worked equation omits it as a simplification; it is included here because
leaving it out would misrepresent the converter's transient/control behavior.
"""

import math
from dataclasses import dataclass

from . import config


@dataclass
class BoostConverterDesign:
    inductance: float  # L, Henries
    capacitance: float  # C, Farads
    duty_cycle: float  # D, at the design operating point
    load_resistance: float  # R, Ohm


def duty_cycle(vin: float, vout: float = config.CONVERTER_VOUT) -> float:
    """D = 1 - Vin/Vout for a boost converter in CCM."""
    return 1.0 - vin / vout


def inductor_average_current(vin: float, power: float) -> float:
    """Average inductor current equals average input current for a boost converter."""
    return power / vin


def size_inductor(
    vin: float = config.CONVERTER_VIN_MIN,
    vout: float = config.CONVERTER_VOUT,
    power: float = config.CONVERTER_PMAX,
    fs: float = config.CONVERTER_SWITCHING_FREQ_HZ,
    ripple_frac: float = config.CONVERTER_INDUCTOR_RIPPLE_FRAC,
) -> float:
    """L = (Vin * D) / (fs * delta_IL), delta_IL = ripple_frac * I_L_avg.

    Sized at the worst case (minimum Vin, i.e. maximum duty cycle and current)
    per CLAUDE.md's boost converter design section.
    """
    d = duty_cycle(vin, vout)
    i_avg = inductor_average_current(vin, power)
    delta_il = ripple_frac * i_avg
    return (vin * d) / (fs * delta_il)


def size_output_capacitor(
    vout: float = config.CONVERTER_VOUT,
    power: float = config.CONVERTER_PMAX,
    fs: float = config.CONVERTER_SWITCHING_FREQ_HZ,
    ripple_frac: float = config.CONVERTER_OUTPUT_RIPPLE_FRAC,
    vin: float = config.CONVERTER_VIN_MIN,
) -> float:
    """C = (Iout * D) / (fs * delta_Vo), delta_Vo = ripple_frac * Vout."""
    d = duty_cycle(vin, vout)
    i_out = power / vout
    delta_vo = ripple_frac * vout
    return (i_out * d) / (fs * delta_vo)


def design_boost_converter(
    vin: float = config.CONVERTER_VIN_MIN,
    vout: float = config.CONVERTER_VOUT,
    power: float = config.CONVERTER_PMAX,
    fs: float = config.CONVERTER_SWITCHING_FREQ_HZ,
) -> BoostConverterDesign:
    return BoostConverterDesign(
        inductance=size_inductor(vin, vout, power, fs),
        capacitance=size_output_capacitor(vout, power, fs, vin=vin),
        duty_cycle=duty_cycle(vin, vout),
        load_resistance=config.CONVERTER_LOAD_RESISTANCE,
    )


@dataclass
class SmallSignalModel:
    omega0: float  # rad/s, resonant frequency of the LC pair
    q_factor: float  # quality factor
    omega_z: float  # rad/s, right-half-plane zero frequency
    dc_gain: float  # Vout/(1-D)^2, low-frequency gain of Gvd(s)


def small_signal_model(design: BoostConverterDesign, vin: float, vout: float = config.CONVERTER_VOUT) -> SmallSignalModel:
    """State-space averaged small-signal control-to-output transfer function.

        Gvd(s) = dc_gain * (1 - s/omega_z) / (1 + s/(Q*omega0) + (s/omega0)^2)

    Standard CCM boost-converter result (Erickson & Maksimovic):
        omega0 = (1 - D) / sqrt(L*C)
        Q      = (1 - D) * R * sqrt(C/L)
        omega_z = (1 - D)^2 * R / L
        dc_gain = Vout / (1 - D)^2
    """
    d = design.duty_cycle
    l, c, r = design.inductance, design.capacitance, design.load_resistance
    omega0 = (1 - d) / math.sqrt(l * c)
    q_factor = (1 - d) * r * math.sqrt(c / l)
    omega_z = (1 - d) ** 2 * r / l
    dc_gain = vout / (1 - d) ** 2
    return SmallSignalModel(omega0=omega0, q_factor=q_factor, omega_z=omega_z, dc_gain=dc_gain)


def critical_inductance(vin: float, vout: float, power: float, fs: float = config.CONVERTER_SWITCHING_FREQ_HZ) -> float:
    """Minimum L for CCM at this operating point: L_crit = (1-D)^2 * D * R / (2*fs)."""
    d = duty_cycle(vin, vout)
    r = vout**2 / power if power > 0 else float("inf")
    return (1 - d) ** 2 * d * r / (2 * fs)


def is_discontinuous_conduction(
    inductance: float,
    vin: float,
    vout: float,
    power: float,
    fs: float = config.CONVERTER_SWITCHING_FREQ_HZ,
) -> bool:
    """True if the converter drops into DCM at this operating point.

    Equivalent DCM condition: average inductor current is less than half the
    peak-to-peak ripple, i.e. inductor current would reach zero mid-cycle.
    """
    if power <= 0:
        return True
    d = duty_cycle(vin, vout)
    i_avg = inductor_average_current(vin, power)
    delta_il = (vin * d) / (fs * inductance)
    return i_avg < delta_il / 2
