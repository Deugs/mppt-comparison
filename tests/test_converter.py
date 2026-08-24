import pytest

from src import config
from src.converter import (critical_inductance, design_boost_converter,
                           duty_cycle, is_discontinuous_conduction,
                           small_signal_model)


def test_duty_cycle_worst_case_matches_claude_md_worked_example():
    d = duty_cycle(vin=config.CONVERTER_VIN_MIN, vout=config.CONVERTER_VOUT)
    assert d == pytest.approx(0.5833, abs=1e-3)


def test_load_resistance_matches_claude_md_worked_example():
    assert config.CONVERTER_LOAD_RESISTANCE == pytest.approx(9.2, abs=0.05)


def test_inductor_sizing_matches_claude_md_worked_example():
    design = design_boost_converter(
        vin=config.CONVERTER_VIN_MIN,
        vout=config.CONVERTER_VOUT,
        power=config.CONVERTER_PMAX,
        fs=config.CONVERTER_SWITCHING_FREQ_HZ,
    )
    # CLAUDE.md worked example: L ~ 154 uH -> select 150-220 uH.
    assert design.inductance == pytest.approx(154e-6, rel=0.02)


def test_design_is_in_ccm_at_full_load():
    design = design_boost_converter(
        vin=config.CONVERTER_VIN_MIN, power=config.CONVERTER_PMAX
    )
    assert not is_discontinuous_conduction(
        design.inductance,
        vin=config.CONVERTER_VIN_MIN,
        vout=config.CONVERTER_VOUT,
        power=config.CONVERTER_PMAX,
    )


def test_design_enters_dcm_at_light_load():
    """Document DCM behavior at low irradiance / light load per CLAUDE.md."""
    design = design_boost_converter(
        vin=config.CONVERTER_VIN_MIN, power=config.CONVERTER_PMAX
    )
    light_load_power = config.CONVERTER_PMAX * 0.05
    assert is_discontinuous_conduction(
        design.inductance,
        vin=config.CONVERTER_VIN_MIN,
        vout=config.CONVERTER_VOUT,
        power=light_load_power,
    )


def test_critical_inductance_below_designed_inductance_at_full_load():
    design = design_boost_converter(
        vin=config.CONVERTER_VIN_MIN, power=config.CONVERTER_PMAX
    )
    l_crit = critical_inductance(
        vin=config.CONVERTER_VIN_MIN,
        vout=config.CONVERTER_VOUT,
        power=config.CONVERTER_PMAX,
    )
    assert l_crit < design.inductance


def test_small_signal_model_is_stable_second_order_system():
    design = design_boost_converter(
        vin=config.CONVERTER_VIN_MIN, power=config.CONVERTER_PMAX
    )
    model = small_signal_model(design, vin=config.CONVERTER_VIN_MIN)
    assert model.omega0 > 0
    assert model.q_factor > 0
    assert model.omega_z > 0
    assert model.dc_gain > config.CONVERTER_VOUT
