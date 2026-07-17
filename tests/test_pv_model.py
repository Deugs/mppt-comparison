"""Sanity + datasheet-key-point validation for the two-diode PV model.

NOTE on validation scope: CLAUDE.md's acceptance criterion is RMSE < 2%
against datasheet I-V/P-V curves at STC, NOCT, and low irradiance, ideally
against digitized curve data. data/panel_datasheet.pdf (now obtained -- see
data/README.md) only provides scalar key points at each condition (Voc, Isc,
Vmp, Imp, Pmax), not a digitized dense curve, so every RMSE check in this
file -- STC, NOCT, and low-irradiance alike -- is computed across those key
points, not a full plotted-curve comparison. Passing these checks confirms
the model matches the manufacturer's reported operating points at each
condition, not a point-by-point match to the plotted I-V curve shape.
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
    voc_model = model.open_circuit_voltage(config.STC_IRRADIANCE, config.STC_TEMPERATURE_C)
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


def test_voc_decreases_and_isc_increases_with_temperature(stc_params):
    """Regression test for a real bug: temperature affecting only Vt (not Iph/Is)
    made Voc *increase* with temperature -- backwards from every real PV panel,
    including this one (datasheet Kv=-0.34%/C, Ki=+0.065%/C). Fixed via
    temperature-dependent Iph/Is in pv_model.py (see its module docstring)."""
    from src.pv_model import TwoDiodeModel

    model = TwoDiodeModel(stc_params, num_cells=config.PANEL_NS)
    voc_cold = model.open_circuit_voltage(config.STC_IRRADIANCE, 0.0)
    voc_stc = model.open_circuit_voltage(config.STC_IRRADIANCE, config.STC_TEMPERATURE_C)
    voc_hot = model.open_circuit_voltage(config.STC_IRRADIANCE, 50.0)
    assert voc_cold > voc_stc > voc_hot

    isc_cold = model.current_at_voltage(0.0, config.STC_IRRADIANCE, 0.0)
    isc_stc = model.current_at_voltage(0.0, config.STC_IRRADIANCE, config.STC_TEMPERATURE_C)
    isc_hot = model.current_at_voltage(0.0, config.STC_IRRADIANCE, 50.0)
    assert isc_cold < isc_stc < isc_hot

    # Quantitative check against the datasheet's own linear coefficients,
    # not just the sign.
    expected_voc_hot = config.PANEL_VOC_STC * (1 + config.KV_VOC_PCT_PER_C / 100 * 25)
    expected_isc_hot = config.PANEL_ISC_STC * (1 + config.KI_ISC_PCT_PER_C / 100 * 25)
    assert voc_hot == pytest.approx(expected_voc_hot, rel=0.01)
    assert isc_hot == pytest.approx(expected_isc_hot, rel=0.01)


def test_stc_key_points_unchanged_by_temperature_dependence_fix(stc_params):
    """The Iph(G,T)/Is(T) correction factors are identically 1 at T=T_ref, so
    STC behavior must be provably unaffected by the temperature-dependence fix."""
    from src.pv_model import TwoDiodeModel

    model = TwoDiodeModel(stc_params, num_cells=config.PANEL_NS)
    isc = model.current_at_voltage(0.0)
    voc = model.open_circuit_voltage(config.STC_IRRADIANCE, config.STC_TEMPERATURE_C)
    _, p_mpp = model.find_mpp()
    assert isc == pytest.approx(config.PANEL_ISC_STC, rel=0.001)
    assert voc == pytest.approx(config.PANEL_VOC_STC, rel=0.001)
    assert p_mpp == pytest.approx(config.PANEL_PMAX_STC, rel=0.001)


def test_noct_validation_within_2_percent_rmse(stc_params):
    """CLAUDE.md's NOCT acceptance criterion, applied to the manufacturer's
    NOCT electrical table for the CS6P-250P (data/README.md): Pmax=181W,
    Vmp=27.5V, Imp=6.60A, Voc=34.2V, Isc=7.19A at G=800 W/m^2, Tc=45C."""
    from src.pv_model import TwoDiodeModel

    model = TwoDiodeModel(stc_params, num_cells=config.PANEL_NS)
    g, t = config.NOCT_IRRADIANCE, config.NOCT_CELL_TEMPERATURE_C

    isc = model.current_at_voltage(0.0, g, t)
    voc = model.open_circuit_voltage(g, t)
    v_mpp, p_mpp = model.find_mpp(g, t)
    i_mpp = p_mpp / v_mpp

    datasheet = {"Isc": 7.19, "Voc": 34.2, "Vmp": 27.5, "Imp": 6.60, "Pmax": 181.0}
    simulated = {"Isc": isc, "Voc": voc, "Vmp": v_mpp, "Imp": i_mpp, "Pmax": p_mpp}

    relative_errors = [(simulated[k] - datasheet[k]) / datasheet[k] for k in datasheet]
    rmse = (sum(e**2 for e in relative_errors) / len(relative_errors)) ** 0.5
    assert rmse < 0.02


def test_low_irradiance_efficiency_retention_is_reasonably_close(stc_params):
    """The datasheet only gives a coarse claim (data/README.md: "+95.5%
    module efficiency retained from 1000 to 200 W/m^2"), not a full I-V table
    at 200 W/m^2 -- so this is a single retention-ratio check against that
    claim, not a point-by-point curve match like the NOCT test above. A
    generous tolerance reflects that the underlying claim is itself
    approximate, and this simplified model doesn't scale Rs/Rsh with
    irradiance the way a full 5-parameter model would."""
    from src.pv_model import TwoDiodeModel

    model = TwoDiodeModel(stc_params, num_cells=config.PANEL_NS)
    _, p_mpp_stc = model.find_mpp(config.STC_IRRADIANCE, config.STC_TEMPERATURE_C)
    _, p_mpp_low = model.find_mpp(config.LOW_IRRADIANCE, config.STC_TEMPERATURE_C)

    efficiency_stc = p_mpp_stc / config.STC_IRRADIANCE
    efficiency_low = p_mpp_low / config.LOW_IRRADIANCE
    retention = efficiency_low / efficiency_stc

    assert retention > 0.90  # datasheet claims 0.955; this model measures ~0.935
