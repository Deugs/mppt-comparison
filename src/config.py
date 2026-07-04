"""Single source of truth for all physical constants and design parameters.

Nothing in src/algorithms, src/pv_model.py, or src/converter.py should hardcode
a physical constant or panel/converter parameter — import it from here instead.
"""

# --- Universal physical constants ---
BOLTZMANN_CONSTANT = 1.380649e-23  # J/K
ELECTRON_CHARGE = 1.602176634e-19  # C

# --- Standard Test Conditions / NOCT reference points ---
STC_IRRADIANCE = 1000.0  # W/m^2
STC_TEMPERATURE_C = 25.0  # deg C
NOCT_IRRADIANCE = 800.0  # W/m^2
NOCT_AMBIENT_TEMPERATURE_C = 20.0  # deg C
NOCT_CELL_TEMPERATURE_C = 45.0  # deg C, approximate per datasheet NOCT rating
LOW_IRRADIANCE = 200.0  # W/m^2

# --- Reference panel: Canadian Solar CS6P-250P (60-cell, poly) ---
# Values below are transcribed from the manufacturer's summary datasheet table.
# See data/README.md: the full datasheet PDF has not yet been obtained, so the
# temperature coefficients (KI_ISC, KV_VOC, KP_PMAX) are left unset rather than
# guessed. Do not fill these in from memory/estimate -- pull them from the PDF.
PANEL_VOC_STC = 37.2  # V
PANEL_ISC_STC = 8.87  # A
PANEL_VMP_STC = 30.1  # V
PANEL_IMP_STC = 8.30  # A
PANEL_PMAX_STC = 250.0  # W
PANEL_NS = 60  # cells in series

KI_ISC_PCT_PER_C = None  # TODO(data/README.md): temp coeff of Isc, %/degC
KV_VOC_PCT_PER_C = None  # TODO(data/README.md): temp coeff of Voc, %/degC
KP_PMAX_PCT_PER_C = None  # TODO(data/README.md): temp coeff of Pmax, %/degC

# --- Bypass diode configuration ---
# One bypass diode per 20 cells is standard industry practice; see CLAUDE.md
# "Bypass Diodes" section for the citation flag on this design choice.
CELLS_PER_BYPASS_GROUP = 20
NUM_BYPASS_DIODES = PANEL_NS // CELLS_PER_BYPASS_GROUP  # 3 for a 60-cell panel
BYPASS_DIODE_VF = 0.7  # V, ideal-diode forward drop when conducting

# --- Two-diode model parameter extraction bounds ---
# Used as scipy.optimize bounds/initial guesses, NOT final fixed values -- the
# actual (Rs, Rsh, a1, a2, Iph, Is1, Is2) for this panel are the output of
# extraction against the four datasheet key points (Voc, Isc, Vmp, Imp).
DIODE1_IDEALITY_BOUNDS = (0.95, 1.05)  # a1, ~1.0 per CLAUDE.md
DIODE2_IDEALITY_BOUNDS = (1.2, 2.0)  # a2
SERIES_RESISTANCE_BOUNDS = (0.2, 0.5)  # Rs, Ohm
SHUNT_RESISTANCE_BOUNDS = (200.0, 1000.0)  # Rsh, Ohm
SATURATION_CURRENT_INITIAL_GUESS = 1e-10  # A, for Is1 and Is2

# --- Boost converter design ---
CONVERTER_SWITCHING_FREQ_HZ = 20e3
CONVERTER_VIN_MIN = 20.0  # V
CONVERTER_VIN_MAX = 40.0  # V
CONVERTER_VOUT = 48.0  # V
CONVERTER_PMAX = 250.0  # W
CONVERTER_INDUCTOR_RIPPLE_FRAC = 0.30  # fraction of average inductor current
CONVERTER_OUTPUT_RIPPLE_FRAC = 0.01  # fraction of output voltage
CONVERTER_LOAD_RESISTANCE = CONVERTER_VOUT**2 / CONVERTER_PMAX  # ~9.2 Ohm

# --- MPPT / scenario constants ---
MPPT_CONVERGENCE_THRESHOLD = 0.02  # 2% of MPP, per CLAUDE.md convention
SETTLING_WINDOW_S = 0.100  # must stay within threshold for >=100ms
MONTE_CARLO_RUNS = 50
SENSOR_NOISE_STD_FRAC = 0.01  # +/-1% Gaussian noise on V and I
