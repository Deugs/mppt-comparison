"""Two-diode PV model with bypass diodes, and datasheet parameter extraction.

    I = Iph - Is1*[exp((V + I*Rs)/(a1*Vt)) - 1]
            - Is2*[exp((V + I*Rs)/(a2*Vt)) - 1]
            - (V + I*Rs)/Rsh

where Vt = a * num_cells * k * T / q is the module- (or group-) level thermal
voltage for the series-connected cell string being modeled.

Citation (mandatory, per CLAUDE.md): Ishaque, K., Salam, Z., and Taheri, H.
(2011). "Simple, fast and accurate two-diode model for photovoltaic modules."
Solar Energy Materials and Solar Cells, 95, 586-594. Do NOT cite Villalva et
al. (2009) for the two-diode model itself -- that paper's contribution is a
single-diode 3-point extraction method.
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq, least_squares

from . import config


def thermal_voltage(temperature_c: float, ideality: float, num_cells: int) -> float:
    """Module-/group-level thermal voltage a * num_cells * k * T / q, in volts."""
    temperature_k = temperature_c + 273.15
    return ideality * num_cells * config.BOLTZMANN_CONSTANT * temperature_k / config.ELECTRON_CHARGE


@dataclass
class TwoDiodeParameters:
    iph: float  # photocurrent at STC irradiance, A
    is1: float  # diode 1 (diffusion) saturation current, A
    is2: float  # diode 2 (recombination) saturation current, A
    rs: float  # series resistance, Ohm
    rsh: float  # shunt resistance, Ohm
    a1: float  # diode 1 ideality factor
    a2: float  # diode 2 ideality factor


class TwoDiodeModel:
    """Two-diode equivalent circuit for one series-connected cell string.

    A "cell string" here is whatever block shares a single set of diode
    parameters and a single irradiance/temperature: a whole module, or one
    bypass-diode-protected group of cells within a module (see PVModuleGroup).
    """

    def __init__(self, params: TwoDiodeParameters, num_cells: int):
        self.params = params
        self.num_cells = num_cells

    def _residual(self, i: float, v: float, irradiance: float, temperature_c: float) -> float:
        p = self.params
        iph = p.iph * irradiance / config.STC_IRRADIANCE
        vt1 = thermal_voltage(temperature_c, p.a1, self.num_cells)
        vt2 = thermal_voltage(temperature_c, p.a2, self.num_cells)
        vd = v + i * p.rs
        i_d1 = p.is1 * np.expm1(vd / vt1)
        i_d2 = p.is2 * np.expm1(vd / vt2)
        i_sh = vd / p.rsh
        return iph - i_d1 - i_d2 - i_sh - i

    def current_at_voltage(
        self,
        v: float,
        irradiance: float = config.STC_IRRADIANCE,
        temperature_c: float = config.STC_TEMPERATURE_C,
    ) -> float:
        """Solve the implicit two-diode equation for current at a given voltage.

        Returns 0.0 for V beyond the (irradiance/temperature-dependent) open-
        circuit voltage, where the forward-biased branch has no solution.
        """
        p = self.params
        iph = p.iph * irradiance / config.STC_IRRADIANCE
        lo, hi = -1e-3, iph + 1.0
        try:
            return brentq(self._residual, lo, hi, args=(v, irradiance, temperature_c), xtol=1e-10, maxiter=200)
        except ValueError:
            return 0.0

    def voltage_at_current(
        self,
        i: float,
        irradiance: float = config.STC_IRRADIANCE,
        temperature_c: float = config.STC_TEMPERATURE_C,
    ):
        """Solve for voltage at a forced current (series-string context).

        Returns None if `i` exceeds this string's own short-circuit current at
        the given irradiance -- i.e. it cannot stay forward-biased and must be
        bypassed by its parallel diode. Callers (PVModuleGroup) handle the
        clamp; this method only reports the forward-biased solution.
        """
        isc_here = self.current_at_voltage(0.0, irradiance, temperature_c)
        if i > isc_here:
            return None
        voc_est = self._open_circuit_voltage(irradiance, temperature_c)
        lo, hi = -1e-2, voc_est * 1.3
        return brentq(
            lambda v: self._residual(i, v, irradiance, temperature_c),
            lo,
            hi,
            xtol=1e-10,
            maxiter=200,
        )

    def _open_circuit_voltage(self, irradiance: float, temperature_c: float) -> float:
        return brentq(
            lambda v: self._residual(0.0, v, irradiance, temperature_c),
            1e-6,
            1.0 * self.num_cells,
            xtol=1e-10,
            maxiter=200,
        )

    def iv_curve(
        self,
        voltages: np.ndarray,
        irradiance: float = config.STC_IRRADIANCE,
        temperature_c: float = config.STC_TEMPERATURE_C,
    ) -> np.ndarray:
        return np.array([self.current_at_voltage(v, irradiance, temperature_c) for v in voltages])

    def power_at_voltage(
        self,
        v: float,
        irradiance: float = config.STC_IRRADIANCE,
        temperature_c: float = config.STC_TEMPERATURE_C,
    ) -> float:
        return v * self.current_at_voltage(v, irradiance, temperature_c)


class PVModuleGroup:
    """One bypass-diode-protected group of `CELLS_PER_BYPASS_GROUP` cells."""

    def __init__(self, params: TwoDiodeParameters, num_cells: int = config.CELLS_PER_BYPASS_GROUP):
        self.model = TwoDiodeModel(params, num_cells=num_cells)

    def voltage_at_current(
        self,
        i: float,
        irradiance: float = config.STC_IRRADIANCE,
        temperature_c: float = config.STC_TEMPERATURE_C,
    ) -> float:
        v = self.model.voltage_at_current(i, irradiance, temperature_c)
        if v is None:
            # Forced current exceeds this group's short-circuit current: the
            # group goes into reverse bias and its bypass diode conducts.
            return -config.BYPASS_DIODE_VF
        return v


class PVModule:
    """A full panel composed of bypass-diode-protected groups in series.

    Groups default to identical parameters/irradiance (uniform illumination);
    pass a list of per-group irradiance values to model intra-module shading.
    """

    def __init__(self, params: TwoDiodeParameters, num_groups: int = config.NUM_BYPASS_DIODES):
        self.groups = [PVModuleGroup(params) for _ in range(num_groups)]

    def voltage_at_current(
        self,
        i: float,
        irradiance,
        temperature_c: float = config.STC_TEMPERATURE_C,
    ) -> float:
        irradiances = irradiance if hasattr(irradiance, "__len__") else [irradiance] * len(self.groups)
        return sum(g.voltage_at_current(i, g_irr, temperature_c) for g, g_irr in zip(self.groups, irradiances))


class PVString:
    """Modules connected in series (e.g. the multi-panel partial-shading scenarios)."""

    def __init__(self, modules: list[PVModule]):
        self.modules = modules

    def voltage_at_current(self, i: float, irradiances, temperature_c: float = config.STC_TEMPERATURE_C) -> float:
        return sum(m.voltage_at_current(i, irr, temperature_c) for m, irr in zip(self.modules, irradiances))

    def pv_curve(self, currents: np.ndarray, irradiances, temperature_c: float = config.STC_TEMPERATURE_C):
        voltages = np.array([self.voltage_at_current(i, irradiances, temperature_c) for i in currents])
        powers = voltages * currents
        return voltages, powers


def extract_two_diode_parameters(
    voc: float,
    isc: float,
    vmp: float,
    imp: float,
    num_cells: int = config.PANEL_NS,
    temperature_c: float = config.STC_TEMPERATURE_C,
) -> TwoDiodeParameters:
    """Fit two-diode parameters to the four datasheet key points (Voc, Isc, Vmp, Imp).

    Simplification -- flag for the paper's methodology section: a1 is fixed at
    the midpoint of DIODE1_IDEALITY_BOUNDS (~1.0) rather than fit, and
    Is1 = Is2 = Is0 is solved analytically from the Voc boundary condition at
    every optimizer iteration. This leaves 4 free variables (Iph, Rs, Rsh, a2)
    fit against 3 residual conditions (Isc match, Imp-at-Vmp match, dP/dV = 0
    at the MPP) via bounded nonlinear least squares. The system is therefore
    under-determined by one degree of freedom relative to the full iterative
    procedure in Ishaque, Salam & Taheri (2011), which this extraction should
    be reconciled against before being treated as final for publication (see
    CLAUDE.md "Two-Diode Model" / "Citation Flags").
    """
    a1 = sum(config.DIODE1_IDEALITY_BOUNDS) / 2

    def build_model(iph: float, rs: float, rsh: float, a2: float) -> TwoDiodeModel:
        vt1 = thermal_voltage(temperature_c, a1, num_cells)
        vt2 = thermal_voltage(temperature_c, a2, num_cells)
        denom = np.expm1(voc / vt1) + np.expm1(voc / vt2)
        is0 = max((iph - voc / rsh) / denom, 1e-15)
        params = TwoDiodeParameters(iph=iph, is1=is0, is2=is0, rs=rs, rsh=rsh, a1=a1, a2=a2)
        return TwoDiodeModel(params, num_cells=num_cells)

    def residuals(x: np.ndarray) -> np.ndarray:
        iph, rs, rsh, a2 = x
        model = build_model(iph, rs, rsh, a2)
        i_at_short = model.current_at_voltage(0.0, temperature_c=temperature_c)
        i_at_vmp = model.current_at_voltage(vmp, temperature_c=temperature_c)
        dv = 1e-4
        p_minus = (vmp - dv) * model.current_at_voltage(vmp - dv, temperature_c=temperature_c)
        p_plus = (vmp + dv) * model.current_at_voltage(vmp + dv, temperature_c=temperature_c)
        dpdv = (p_plus - p_minus) / (2 * dv)
        return np.array(
            [
                (i_at_short - isc) / isc,
                (i_at_vmp - imp) / imp,
                dpdv / (vmp * imp),
            ]
        )

    x0 = [
        isc * 1.01,
        sum(config.SERIES_RESISTANCE_BOUNDS) / 2,
        sum(config.SHUNT_RESISTANCE_BOUNDS) / 2,
        sum(config.DIODE2_IDEALITY_BOUNDS) / 2,
    ]
    lower = [isc, config.SERIES_RESISTANCE_BOUNDS[0], config.SHUNT_RESISTANCE_BOUNDS[0], config.DIODE2_IDEALITY_BOUNDS[0]]
    upper = [isc * 1.1, config.SERIES_RESISTANCE_BOUNDS[1], config.SHUNT_RESISTANCE_BOUNDS[1], config.DIODE2_IDEALITY_BOUNDS[1]]

    result = least_squares(residuals, x0, bounds=(lower, upper), xtol=1e-13, ftol=1e-13, gtol=1e-13)
    iph, rs, rsh, a2 = result.x
    return build_model(iph, rs, rsh, a2).params
