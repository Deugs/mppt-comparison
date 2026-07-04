"""Sanity + datasheet-key-point validation for the two-diode PV model.

NOTE on validation scope: CLAUDE.md's acceptance criterion is RMSE < 2%
against full datasheet I-V/P-V curves at STC, NOCT, and low irradiance. That
requires digitized datasheet curve data, which depends on data/panel_datasheet.pdf
(not yet obtained -- see data/README.md). Until then, this file validates
against the four scalar key points (Voc, Isc, Vmp, Imp) that CLAUDE.md's
summary table provides, which is also exactly what extract_two_diode_parameters
fits against -- so passing these checks confirms the extraction converged
correctly, not yet that the full curve matches the manufacturer's plotted curve.
"""

import numpy as np
import pytest

from src import config
from src.pv_model import PVModule, PVModuleGroup, extract_two_diode_parameters


@pytest.fixture(scope="module")
def stc_params():
    return extract_two_diode_parameters(
        voc=config.PANEL_VOC_STC,
        isc=config.PANEL_ISC_STC,
        vmp=config.PANEL_VMP_STC,
        imp=config.PANEL_IMP_STC,
    )


def test_extraction_parameters_within_config_bounds(stc_params):
    assert config.SERIES_RESISTANCE_BOUNDS[0] <= stc_params.rs <= config.SERIES_RESISTANCE_BOUNDS[1]
    assert config.SHUNT_RESISTANCE_BOUNDS[0] <= stc_params.rsh <= config.SHUNT_RESISTANCE_BOUNDS[1]
    assert config.DIODE2_IDEALITY_BOUNDS[0] <= stc_params.a2 <= config.DIODE2_IDEALITY_BOUNDS[1]


def test_short_circuit_current_matches_datasheet(stc_params):
    from src.pv_model import TwoDiodeModel

    model = TwoDiodeModel(stc_params, num_cells=config.PANEL_NS)
    isc_model = model.current_at_voltage(0.0)
    assert isc_model == pytest.approx(config.PANEL_ISC_STC, rel=0.02)


def test_open_circuit_voltage_matches_datasheet(stc_params):
    from src.pv_model import TwoDiodeModel

    model = TwoDiodeModel(stc_params, num_cells=config.PANEL_NS)
    voc_model = model._open_circuit_voltage(config.STC_IRRADIANCE, config.STC_TEMPERATURE_C)
    assert voc_model == pytest.approx(config.PANEL_VOC_STC, rel=0.02)


def test_mpp_matches_datasheet_within_2_percent(stc_params):
    """CLAUDE.md acceptance criterion: RMSE/error < 2% (applied here to Pmax)."""
    from src.pv_model import TwoDiodeModel

    model = TwoDiodeModel(stc_params, num_cells=config.PANEL_NS)
    voltages = np.linspace(0.1, config.PANEL_VOC_STC * 0.999, 400)
    powers = np.array([model.power_at_voltage(v) for v in voltages])
    p_max_model = powers.max()
    p_max_datasheet = config.PANEL_PMAX_STC
    relative_error = abs(p_max_model - p_max_datasheet) / p_max_datasheet
    assert relative_error < 0.02


def test_power_curve_is_unimodal_under_uniform_illumination(stc_params):
    from src.pv_model import TwoDiodeModel

    model = TwoDiodeModel(stc_params, num_cells=config.PANEL_NS)
    voltages = np.linspace(0.1, config.PANEL_VOC_STC * 0.999, 200)
    powers = np.array([model.power_at_voltage(v) for v in voltages])
    peak_idx = np.argmax(powers)
    assert np.all(np.diff(powers[: peak_idx + 1]) >= -1e-6)
    assert np.all(np.diff(powers[peak_idx:]) <= 1e-6)


def test_reduced_irradiance_reduces_short_circuit_current(stc_params):
    from src.pv_model import TwoDiodeModel

    model = TwoDiodeModel(stc_params, num_cells=config.PANEL_NS)
    isc_full = model.current_at_voltage(0.0, irradiance=1000.0)
    isc_half = model.current_at_voltage(0.0, irradiance=500.0)
    assert isc_half < isc_full
    assert isc_half == pytest.approx(isc_full * 0.5, rel=0.05)


def test_bypass_diode_clamps_heavily_shaded_group(stc_params):
    """A group forced to carry more current than its own Isc must bypass at -Vf."""
    shaded_group = PVModuleGroup(stc_params)
    unshaded_isc = shaded_group.model.current_at_voltage(0.0, irradiance=config.STC_IRRADIANCE)

    forced_current = unshaded_isc  # what the string, at full irradiance, wants to push
    v = shaded_group.voltage_at_current(forced_current, irradiance=200.0)
    assert v == pytest.approx(-config.BYPASS_DIODE_VF)


def test_module_voltage_is_sum_of_group_voltages(stc_params):
    module = PVModule(stc_params)
    low_current = 0.5
    v_module = module.voltage_at_current(low_current, irradiance=config.STC_IRRADIANCE)
    v_single_group = module.groups[0].voltage_at_current(low_current, irradiance=config.STC_IRRADIANCE)
    assert v_module == pytest.approx(v_single_group * len(module.groups), rel=1e-6)
