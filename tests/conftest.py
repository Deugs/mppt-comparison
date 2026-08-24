import pytest

from src import config
from src.pv_model import TwoDiodeModel, extract_two_diode_parameters


@pytest.fixture(scope="session")
def pv_model_stc():
    """Two-diode model for the reference panel, fit to STC datasheet key points."""
    params = extract_two_diode_parameters(
        voc=config.PANEL_VOC_STC,
        isc=config.PANEL_ISC_STC,
        vmp=config.PANEL_VMP_STC,
        imp=config.PANEL_IMP_STC,
    )
    return TwoDiodeModel(params, num_cells=config.PANEL_NS)
