"""Single source of truth for all physical constants and design parameters.

Nothing in src/algorithms, src/pv_model.py, or src/converter.py should hardcode
a physical constant or panel/converter parameter — import it from here instead.
"""

# --- Universal physical constants ---
BOLTZMANN_CONSTANT = 1.380649e-23  # J/K
ELECTRON_CHARGE = 1.602176634e-19  # C

# Silicon bandgap energy at STC, eV. Standard value used throughout the PV
# modeling literature for the diode saturation current's temperature
# dependence (Is ~ T^3 * exp(-Eg/(a*k*T))); see pv_model.py's temperature-
# scaling docstring and De Soto, W., Klein, S.A., and Beckman, W.A. (2006).
# "Improvement and validation of a model for photovoltaic array
# performance." Solar Energy, 80(1), 78-88.
PV_BANDGAP_EV = 1.121

# --- Standard Test Conditions / NOCT reference points ---
STC_IRRADIANCE = 1000.0  # W/m^2
STC_TEMPERATURE_C = 25.0  # deg C
NOCT_IRRADIANCE = 800.0  # W/m^2
NOCT_AMBIENT_TEMPERATURE_C = 20.0  # deg C
NOCT_CELL_TEMPERATURE_C = 45.0  # deg C, approximate per datasheet NOCT rating
LOW_IRRADIANCE = 200.0  # W/m^2

# --- Reference panel: Canadian Solar CS6P-250P (60-cell, poly) ---
# Values below are transcribed from the manufacturer's full datasheet,
# "CS6P-230/235/240/245/250P ClearPower" (EN-Rev 3.50, Canadian Solar Inc.,
# 2012), archived at data/panel_datasheet.pdf. STC values cross-checked
# against the datasheet's CS6P-250P column and match exactly.
PANEL_VOC_STC = 37.2  # V
PANEL_ISC_STC = 8.87  # A
PANEL_VMP_STC = 30.1  # V
PANEL_IMP_STC = 8.30  # A
PANEL_PMAX_STC = 250.0  # W
PANEL_NS = 60  # cells in series

# Temperature coefficients, from the datasheet's "Temperature Characteristics"
# table (same for all wattage variants in the CS6P-P series, incl. 250P).
KI_ISC_PCT_PER_C = 0.065  # temp coeff of Isc, %/degC
KV_VOC_PCT_PER_C = -0.34  # temp coeff of Voc, %/degC
KP_PMAX_PCT_PER_C = -0.43  # temp coeff of Pmax, %/degC

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

# Duty cycle clamp shared by all algorithms -- keeps the operating point off
# the D=0/D=1 singularities of the boost converter's R_in = R*(1-D)^2 relation.
MPPT_DUTY_MIN = 0.05
MPPT_DUTY_MAX = 0.90

# --- Perturb & Observe (adaptive step size) ---
# Citation (CLAUDE.md, mandatory): Femia, N., et al. (2005). "Optimization of
# perturb and observe maximum power point tracking method." IEEE Trans. Power
# Electron., 20(4), 963-973.
PO_STEP_LARGE = 0.01  # duty-cycle step when far from MPP
PO_STEP_SMALL = 0.001  # duty-cycle step when near MPP
PO_DPDV_THRESHOLD = 2.0  # W/V; |dP/dV| above this counts as "far from MPP"

# --- Incremental Conductance ---
# Citation (CLAUDE.md, mandatory): Hussein, K.H., et al. (1995). "Maximum
# photovoltaic power tracking: an algorithm for rapidly changing atmospheric
# conditions." IEE Proc.-Gener. Transm. Distrib., 142(1), 59-64.
INC_COND_STEP = 0.001  # fixed duty-cycle step
INC_COND_DV_EPSILON = 1e-3  # V; |dV| below this triggers the dV~=0 boundary case
INC_COND_TOLERANCE = 1e-3  # S; |dI/dV - (-I/V)| below this counts as "at MPP"

# --- Fuzzy Logic Controller ---
# Citation flags (CLAUDE.md, mandatory): 7x7 membership-function/rule-base
# precedent needs a literature citation; each rule's physical justification
# must be derivable (see src/algorithms/fuzzy_logic.py). E_SCALE/CE_SCALE
# below are normalization gains mapping raw dP/dV (and its step-to-step
# change) into the fuzzy engine's [-1, 1] universe of discourse. This
# panel's dP/dV is highly asymmetric (~+8.9 W/V near V=0, vs. a steep
# negative rolloff to roughly -76 W/V approaching Voc); E_SCALE=40 was
# chosen from a grid search (tests/test_fuzzy_logic.py's convergence
# sanity checks) over E_SCALE in [10, 100] and CE_SCALE in [0.2, 1.0] --
# smaller values saturate too easily near the MPP and sustain a limit-cycle
# oscillation instead of converging (e.g. E_SCALE=10 gave ~7% steady-state
# error with the initial values here). Still flagged as needing validation
# against the full Monte Carlo scenario suite in Phase 3, not just the STC
# sanity case this grid search used.
FUZZY_E_SCALE = 40.0  # W/V
FUZZY_CE_SCALE = 1.0  # normalized-E units per step
FUZZY_OUTPUT_MIN = -0.1  # duty-cycle-step universe of discourse, per CLAUDE.md
FUZZY_OUTPUT_MAX = 0.1
FUZZY_DEFUZZ_POINTS = 201  # discretization resolution for centroid defuzzification
FUZZY_INITIAL_PERTURBATION = 0.01  # bootstrap duty-cycle nudge on the first step (no dV history yet)

# --- Q-learning ---
# Citation (CLAUDE.md, mandatory): Kofinas, P., Doltsinis, S., Dounis, A.I.,
# and Vouros, G.A. (2017). "A reinforcement learning approach for MPPT
# control method of photovoltaic sources." Renewable Energy, 108, 461-473.
QL_N_VOLTAGE_BINS = 30  # CLAUDE.md: "bin voltage into ~20-30 levels"
QL_N_DPDV_BINS = 7  # CLAUDE.md: "dP/dV sign+magnitude into ~5-7 bins"
QL_DPDV_SCALE = 40.0  # W/V; same empirical grounding as FUZZY_E_SCALE
QL_ACTION_STEP = 0.005  # duty-cycle step per action, mirrors P&O's step scale
QL_ALPHA = 0.15  # learning rate
QL_GAMMA = 0.9  # discount factor
QL_EPSILON_START = 1.0
QL_EPSILON_MIN = 0.05
QL_EPSILON_DECAY = 0.985  # per-episode multiplicative decay
QL_TRAINING_EPISODES = 2000
QL_STEPS_PER_EPISODE = 40
# Train/held-out split (CLAUDE.md, mandatory): 700 W/m2 is deliberately
# excluded so tests/test_q_learning.py can verify the policy generalizes
# rather than memorizing the training irradiances. This is a Phase 2
# placeholder using flat irradiance levels on a single uniform module --
# the harder cross-shading-pattern generalization test CLAUDE.md's Known
# Risks section calls for needs Phase 3's multi-panel scenario definitions.
QL_TRAINING_IRRADIANCES = (600.0, 800.0, 1000.0)  # W/m^2

# --- Sliding Mode Control ---
# Sliding surface s = dP/dV; exponential reaching law ds/dt = -k*sign(s) - q*s
# (Gao & Hung 1993), with sign(s) replaced by a boundary-layer saturation for
# chattering mitigation (Slotine & Li 1991). Gains grid-searched (same method
# as FUZZY_E_SCALE/FUZZY_CE_SCALE) against the STC convergence + steady-state
# oscillation sanity checks in tests/test_sliding_mode.py.
# Citations (CLAUDE.md, mandatory): Utkin, V. (1977). "Variable structure
# systems with sliding mode control." IEEE Trans. Autom. Control, 22(2),
# 212-222 (general SMC theory). Gao, W., and Hung, J.C. (1993). "Variable
# structure control of nonlinear systems: A new approach." IEEE Trans. Ind.
# Electron., 40(1), 45-55 (exponential reaching law). Slotine, J.J.E., and
# Li, W. (1991). Applied Nonlinear Control. Prentice Hall (boundary-layer
# chattering mitigation). Still flagged per CLAUDE.md: find and cite the
# specific PV-SMC paper whose surface/reaching-law choice most closely
# matches this one, during the Phase 4 literature review -- not done yet.
SMC_PHI_SCALE = 80.0  # W/V; normalizes dP/dV to the controller's [-1, 1] range
SMC_K = 0.03  # switching-term gain (constant-rate component)
SMC_Q = 0.01  # proportional-term gain (exponential component)
SMC_BOUNDARY = 0.1  # boundary-layer half-width, normalized units
SMC_BOOTSTRAP = 0.01  # initial duty-cycle nudge on the first step (no dV history yet)

# --- Scenario runner ---
MPPT_SAMPLE_PERIOD_S = 0.001  # 1 ms; ~20 boost-converter switching cycles per MPPT decision at 20 kHz

# Partial-shading operating-point solves cost ~10x a single-module solve (one
# root-find per bypass-diode group, ~9 groups for a 3-module string) even
# with PVModuleGroup's Isc/Voc caching. Per CLAUDE.md's Known Risks guidance
# ("profile early; adjust scenario count/resolution if wall-clock time is
# unreasonable rather than cutting an algorithm"), these scenarios are
# steady-state (fixed shading pattern for the whole run) so fine transient
# resolution isn't the point -- sample 10x coarser than the single-module
# scenarios to keep a 50-run Monte Carlo sweep tractable.
PARTIAL_SHADING_SAMPLE_PERIOD_S = 0.01  # 10 ms
