# MPPT Algorithm Comparison — IEEE Journal Publication Plan

**This is Paper 1 of a multi-paper research program.** See `RESEARCH_PROGRAM.md`
for the full roadmap (Papers 2-5: learning-based deep dive, metaheuristic
benchmark, game-theoretic meta-controller, multi-converter cooperative game).
**Do not add GWO, LSTM-PPO, FOCV-P&O, SM-Fuzzy, ANN-MPPT, or any game-theory
content to this file or this codebase** — each belongs to a later paper with
its own scope, and mixing them back in here recreates the exact incoherence
problem the roadmap split was meant to solve.

## Timeline Reality Check
The phased plan below gets you to **submission-ready**, not to acceptance.
IEEE Transactions review cycles typically run 6-18 months with 1-3 revision rounds.
Budget this as a semester-scale commitment. Keep the IEEE Access / preprint fallback
in the TODO — it's not a downgrade, it's insurance if TEC/JPV desk-rejects or a
revision cycle stalls.

**Scope update:** now 5 algorithms (was 4) spanning 4 distinct MPPT paradigms.
This adds real implementation and Monte Carlo runtime — plan Phase 2-3 accordingly
(see revised phase estimates below).

## Overview
Research project comparing Maximum Power Point Tracking (MPPT) algorithms for solar PV systems under varying irradiance conditions, including partial shading. Goal: publishable comparison paper in an IEEE Scopus-indexed journal (target: IEEE Transactions on Energy Conversion, IEEE Transactions on Industrial Electronics, or IEEE Journal of Photovoltaics).

**Key Differentiator:** Pure-Python, fully reproducible simulation framework with open-source release, comparing algorithms across four distinct MPPT design paradigms rather than five variations on one idea. Most comparable work either sticks to classical methods or adds "yet another bio-inspired optimizer" — a corner of the literature that's become saturated and draws reviewer skepticism. This framework instead spans the actual design space: perturbative, rule-based, learning-based, and model-based control.

---

## Novelty Strategy (Critical for IEEE Acceptance)

The comparison of P&O, IncCond, and fuzzy logic is a saturated topic, and so —
increasingly — is "propose yet another bio-inspired swarm optimizer" (PSO-GWO,
PSO-DFO, Zebra/Dung Beetle/Seagull optimization, etc.). To meet IEEE novelty
standards without adding to that pile, this project combines:

1. **Open-source reproducibility:** Pure Python, dependency-locked, CI-tested, Zenodo-DOI release
2. **Rigorous model validation:** Two-diode PV model with bypass diodes, validated against real datasheet with quantitative RMSE
3. **Cross-paradigm algorithm set, not variations on one idea:**
   - P&O — perturbative baseline
   - IncCond — refined perturbative
   - Fuzzy Logic — rule-based
   - Q-learning — learning-based (model-free)
   - Sliding Mode Control (SMC) — model-based nonlinear control, Lyapunov-stable by construction
4. **Comprehensive scenario coverage:** Including rapid fluctuations, sensor noise, and complex partial shading with 3+ local maxima
5. **Statistical rigor:** Monte Carlo simulation (>=50 runs per scenario-algorithm pair) with confidence intervals — this does double duty for Q-learning, where it's also the mechanism for showing the policy generalizes rather than overfitting to one shading pattern

**Proposed paper title angle:** *"A Reproducible Open-Source Framework for Comparative MPPT Evaluation Across Perturbative, Rule-Based, Learning-Based, and Model-Based Control Paradigms Under Partial Shading"*
(trim for length once you see the journal's title conventions — this is a working title, not final)

---

## Tech Stack

| Package | Purpose | Version Lock |
|---------|---------|-------------|
| Python | Runtime | 3.11+ |
| numpy | PV model math, array ops | ^1.24 |
| scipy | Optimization, root-finding (Newton-Raphson for two-diode model) | ^1.11 |
| matplotlib | Publication-quality plots (.png + .svg) | ^3.7 |
| pandas | Results tables, metric logging, long-format CSV | ^2.0 |
| pytest | Sanity checks for each algorithm and model | ^7.4 |
| pytest-cov | Coverage reporting | ^4.1 |
| jupyter | Interactive figure generation notebooks | ^4.0 |

**No MATLAB dependency** — pure Python so results are fully reproducible by reviewers.

---

## Project Structure

```
mppt-comparison/
├── src/
│   ├── config.py              # ALL physical constants & parameters (single source of truth)
│   ├── pv_model.py            # Two-diode model with bypass diodes, parameter extraction
│   ├── converter.py           # Boost converter: state-space averaged model, component sizing
│   ├── algorithms/
│   │   ├── base.py            # Abstract base class: step(v, i, duty_cycle) -> new_duty_cycle
│   │   ├── p_and_o.py         # Perturb & Observe (adaptive step size)
│   │   ├── inc_cond.py        # Incremental Conductance (with boundary handling)
│   │   ├── fuzzy_logic.py     # Fuzzy Logic Controller (7x7 rule base, documented per rule)
│   │   ├── q_learning.py      # Tabular Q-learning: discretized (V, dP/dV) state space, duty-cycle-delta actions
│   │   └── sliding_mode.py    # SMC: sliding surface on dP/dV=0, reaching law, chattering mitigation
│   ├── scenarios.py           # Unified scenario runner (swaps algorithms without special-casing)
│   └── metrics.py             # Tracking efficiency, convergence time, oscillation, energy yield
├── tests/
│   ├── test_pv_model.py       # Validate against datasheet I-V/P-V curves (RMSE < 2%)
│   ├── test_converter.py      # Steady-state and transient validation
│   ├── test_p_and_o.py        # Must find correct MPP at 1000 W/m2, 25C
│   ├── test_inc_cond.py       # Must find correct MPP at 1000 W/m2, 25C
│   ├── test_fuzzy_logic.py    # Must find correct MPP at 1000 W/m2, 25C
│   ├── test_q_learning.py     # Must find correct MPP after training at 1000 W/m2, 25C; also test on held-out shading pattern not seen during training
│   └── test_sliding_mode.py   # Must find correct MPP at 1000 W/m2, 25C; verify no sustained chattering at steady state
├── notebooks/
│   ├── 01_pv_model_validation.ipynb
│   ├── 02_converter_design.ipynb
│   ├── 03_algorithm_comparison.ipynb
│   └── 04_partial_shading_analysis.ipynb
├── results/
│   ├── comparison_table.csv   # Long format: algorithm, scenario, metric, value
│   ├── figures/
│   │   ├── *.png              # Paper figures
│   │   └── *.svg              # Editable vector versions
│   └── monte_carlo/           # Per-run raw data for statistical analysis
├── paper/
│   ├── main.tex               # LaTeX source (IEEEtran class)
│   ├── sections/
│   │   ├── 01_introduction.tex
│   │   ├── 02_literature_review.tex
│   │   ├── 03_pv_model.tex
│   │   ├── 04_converter_model.tex
│   │   ├── 05_algorithms.tex
│   │   ├── 06_scenarios.tex
│   │   ├── 07_results.tex
│   │   └── 08_conclusion.tex
│   └── references.bib
├── data/
│   └── panel_datasheet.pdf    # Locked-in reference panel datasheet
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions: run tests on push
├── requirements.txt           # Pinned dependency versions
├── pyproject.toml             # Modern Python packaging + pytest config
├── README.md                  # Exact reproduction steps
├── LICENSE                    # Open-source license (MIT or BSD-3)
└── claude.md                  # This file
```

---

## PV Model Parameters (Two-Diode Model)

### Reference Panel
**Locked choice: Canadian Solar CS6P-250P** (correct model designation — CS6P series, not CS6K; verified against manufacturer datasheet below).

| Parameter | Value | Source |
|-----------|-------|--------|
| Voc | 37.2 V | Datasheet (verified) |
| Isc | 8.87 A | Datasheet (verified) |
| Vmp | 30.1 V | Datasheet (verified) |
| Imp | 8.30 A | Datasheet (verified) |
| Pmax | 250 W | Datasheet (verified) |
| Ns (cells in series) | 60 | Datasheet |
| a1 (ideality factor, diode 1) | ~1.0 | Extracted via parameter extraction |
| a2 (ideality factor, diode 2) | ~1.2-2.0 | Extracted via parameter extraction |
| Rs (series resistance) | ~0.2-0.5 Ohm | Extracted via parameter extraction |
| Rsh (shunt resistance) | ~200-1000 Ohm | Extracted via parameter extraction |
| Iph (photocurrent) | ~8.9 A | Computed from irradiance/temperature |
| Is1, Is2 (saturation currents) | ~1e-10 A | Extracted via parameter extraction |
| Ki (temp coeff of Isc) | Pull exact value from datasheet PDF | Datasheet |
| Kv (temp coeff of Voc) | Pull exact value from datasheet PDF | Datasheet |

**Action item:** download the full CS6P-250P datasheet PDF (not just the summary
table above) to get exact Ki/Kv temperature coefficients before running parameter
extraction — these vary slightly by print revision and matter for the NOCT validation point.

### Two-Diode Model Equations
```
I = Iph - Is1[exp((V + I*Rs)/(a1*Vt)) - 1] - Is2[exp((V + I*Rs)/(a2*Vt)) - 1] - (V + I*Rs)/Rsh
```
where Vt = kT/q (thermal voltage).

### Parameter Extraction Method
Use **Newton-Raphson** or **Levenberg-Marquardt** to extract Rs, Rsh, a1, a2, Is1, Is2 from datasheet points (Voc, Isc, Vmp, Imp) at STC.

**Citations:**
- Two-diode model: Ishaque, K., Salam, Z., and Taheri, H. (2011). "Simple, fast and accurate two-diode model for photovoltaic modules." Solar Energy Materials and Solar Cells, 95, 586-594.
  (Note: this is the correct source for the two-diode approach — do NOT cite Villalva et al. 2009 for this, as that paper's contribution is a single-diode 3-point extraction method, not two-diode.)
- Single-diode baseline / general extraction methodology reference: Villalva, M.G., Gazoli, J.R., and Ruppert Filho, E. (2009). "Comprehensive approach to modeling and simulation of photovoltaic arrays." IEEE Transactions on Power Electronics, 24(5), 1198-1208.

### Bypass Diodes
- One bypass diode per **20 cells** (standard industry practice)
- For 60-cell panel: 3 bypass diodes (each protecting 20 cells)
- Model as ideal diode with Vf = 0.7V when conducting
- **Critical for partial shading:** Without bypass diodes, there are no local maxima to test algorithm global search capability

### Validation Requirement
Before trusting any algorithm results, verify simulated I-V and P-V curves against datasheet curves at:
- STC: 1000 W/m2, 25C
- NOCT: 800 W/m2, 20C ambient (~45C cell)
- Low irradiance: 200 W/m2, 25C

**Acceptance criterion:** RMSE between simulated and datasheet power < 2% across all test points.

---

## Boost Converter Design

### Specifications
| Parameter | Value | Justification |
|-----------|-------|---------------|
| Switching frequency (fs) | 20 kHz | Standard for PV applications; balance of efficiency vs. component size |
| Input voltage range | 20-40 V | Covers Vmp range of 250W panel under varying conditions |
| Output voltage | 48 V | Common DC bus voltage for battery charging |
| Maximum power | 250 W | Matches panel rating |
| Inductor current ripple (delta_IL) | 30% of average | Standard design choice (Erickson & Maksimovic, Fundamentals of Power Electronics) |
| Output voltage ripple (delta_Vo) | 1% of output | Standard for PV applications |

### Component Sizing Equations (document in converter.py docstring)

**Inductor (L):**
```
L = (V_in * D) / (fs * delta_IL)
where D = 1 - V_in/V_out (duty cycle)
```
Size for worst case (minimum V_in = 20V, max D ~ 0.58):
```
L = (20 * 0.58) / (20e3 * 0.3 * 250/20) ~ 154 uH -> select 150-220 uH
```

**Output Capacitor (C):**
```
C = (I_out * D) / (fs * delta_Vo)
```

**State-Space Averaged Model:**
Document the small-signal transfer function for completeness:
```
Gvd(s) = v_hat_o(s)/d_hat(s) = V_out / (1 + s/(Q*omega0) + (s/omega0)^2)
```
where omega0 and Q are derived from L, C, and load resistance.

**Discontinuous Conduction Mode (DCM) Check:**
Verify that converter does not enter DCM at light load / low irradiance. If it does, document impact on MPPT behavior.

### Load
Resistive load: R_load = V_out^2 / P_max = 48^2 / 250 ~ 9.2 Ohm (adjustable for testing)

---

## Algorithms

### Unified Interface
Every algorithm module exposes the same interface:

```python
class MPPTAlgorithm(ABC):
    @abstractmethod
    def step(self, v: float, i: float, duty_cycle: float) -> float:
        # Compute new duty cycle given current voltage, current, and duty cycle.
        pass

    @abstractmethod
    def reset(self):
        # Reset algorithm state for new scenario.
        pass
```

This allows scenarios.py to swap algorithms without special-casing.

### 1. Perturb & Observe (P&O) — Baseline
- **Expected behavior:** Steady-state oscillation around MPP
- **Implementation:** Adaptive step size (not fixed — expected in 2025+ papers)
  - Large step when far from MPP (|dP/dV| > threshold)
  - Small step near MPP (|dP/dV| < threshold)
- **Citation:** Femia, N., et al. (2005). "Optimization of perturb and observe maximum power point tracking method." IEEE Transactions on Power Electronics, 20(4), 963-973.

### 2. Incremental Conductance (IncCond)
- **Principle:** dI/dV vs -I/V comparison
- **Boundary handling:** When dV ~ 0, use dI sign to determine direction
- **Expected behavior:** Reduced oscillation vs. P&O
- **Citation:** Hussein, K.H., et al. (1995). "Maximum photovoltaic power tracking: an algorithm for rapidly changing atmospheric conditions." IEE Proceedings—Generation, Transmission and Distribution, 142(1), 59-64.

### 3. Fuzzy Logic Controller (FLC)
- **Inputs:** Error E = dP/dV, Change in error delta_E = E(k) - E(k-1)
- **Output:** delta_duty cycle
- **Membership functions:** 7 sets — NB, NM, NS, Z, PS, PM, PB
- **Rule base:** 7 x 7 = 49 rules (documented below)

#### Membership Function Design
- **Type:** Triangular (simple, computationally efficient, valid for this application)
- **Universe of discourse:**
  - E: [-1, 1] (normalized dP/dV)
  - delta_E: [-1, 1] (normalized change in error)
  - delta_D: [-0.1, 0.1] (duty cycle step)

#### Rule Base (Documented with Physical Justification)

| E \\ delta_E | NB | NM | NS | Z | PS | PM | PB |
|---------|----|----|----|---|----|----|----|
| **NB** | PB | PB | PM | PM | PS | PS | Z |
| **NM** | PB | PM | PM | PS | PS | Z | NS |
| **NS** | PM | PM | PS | PS | Z | NS | NS |
| **Z** | PM | PS | PS | Z | NS | NS | NM |
| **PS** | PS | PS | Z | NS | NS | NM | NM |
| **PM** | PS | Z | NS | NS | NM | NM | NB |
| **PB** | Z | NS | NS | NM | NM | NB | NB |

**Rule-by-rule physical justification (sample — document all 49 in paper):**
- **R1 (E=NB, delta_E=NB -> delta_D=PB):** Operating point is far below MPP (large negative error) and moving further away (negative change). Apply large positive duty step to move toward MPP rapidly.
- **R25 (E=Z, delta_E=Z -> delta_D=Z):** At MPP with no change — maintain current duty cycle.
- **R49 (E=PB, delta_E=PB -> delta_D=NB):** Far above MPP and moving further away — apply large negative duty step.

#### Defuzzification
- **Method:** Centroid (center of gravity)
- **Justification:** Most common, provides smooth output

#### Sensitivity Analysis (Contribution)
Test reduced rule bases (5x5 = 25 rules, 3x3 = 9 rules) and show performance trade-off. If 5x5 achieves near-equivalent performance, this is a publishable contribution — rule reduction with maintained performance.

### 4. Q-Learning (Model-Free, Learning-Based)
**Design:**
- State space: discretized (V, dP/dV) — bin voltage into ~20-30 levels, dP/dV sign+magnitude into ~5-7 bins
- Action space: {decrease duty, hold, increase duty} with a fixed or adaptive step, mirroring P&O's action set for a fair comparison
- Reward: instantaneous power P(k), or ΔP to encourage climbing
- Exploration: epsilon-greedy, decaying over training episodes
- **Training protocol (critical for validity):** train on a subset of shading patterns/irradiance profiles, evaluate on held-out patterns not seen during training. This train/test split is what makes the Monte Carlo statistical framework meaningful for this algorithm — it's not just noise-robustness, it's a generalization check.
- Citation: Kofinas, P., Doltsinis, S., Dounis, A.I., and Vouros, G.A. (2017). "A reinforcement learning approach for MPPT control method of photovoltaic sources." Renewable Energy, 108, 461-473.

**Risk to flag in the paper:** results should report performance separately on
training-distribution scenarios vs. held-out scenarios — conflating them would
overstate real-world performance.

### 5. Sliding Mode Control (SMC) — Model-Based Nonlinear Control
**Design:**
- Sliding surface: typically s = dP/dV (drives the system toward the MPP condition dP/dV = 0)
- Reaching law: choose exponential or power reaching law; document the choice and its effect on chattering
- Chattering mitigation: replace the sign function with a sigmoid or saturation function (boundary layer method) — this is a known SMC weakness reviewers will ask about if left unaddressed
- Lyapunov stability: include a brief stability argument (V = 0.5*s^2, show dV/dt < 0) in the methodology section — this is exactly the kind of rigor that appeals to TEC/TIE reviewers
- **Note:** unlike the two-diode citation situation, there is no single "classic" SMC-MPPT
  paper the way Femia (2005) is for P&O — the literature has many valid variants
  (surface choice, reaching law, converter topology). Pick your specific surface/reaching-law
  combination first, then find and cite the paper whose design most closely matches it,
  rather than picking a citation first and reverse-engineering the design to match.
  General SMC theory foundation: Utkin, V. (1977). "Variable structure systems with
  sliding mode control." IEEE Transactions on Automatic Control, 22(2), 212-222.

---

## Test Scenarios

Run all algorithms through each scenario. Use **identical random seeds** for fair comparison. Run **Monte Carlo: >=50 independent runs per scenario-algorithm pair** with randomized initial conditions.

### Scenario 1: Steady-State (Baseline Validation)
- Irradiance: 1000 W/m2
- Temperature: 25C
- Duration: 2 seconds (simulated)
- Purpose: Validate each algorithm finds correct MPP; compute steady-state oscillation

### Scenario 2: Multi-Level Irradiance
- Irradiance sweep: 200 -> 400 -> 600 -> 800 -> 1000 W/m2
- Temperature: 25C (constant)
- Step duration: 1 second per level
- Purpose: Test tracking across full operating range

### Scenario 3: Step-Change Irradiance
- 1000 -> 600 -> 1000 W/m2
- Step at t = 1s and t = 3s
- Temperature: 25C
- Purpose: Test dynamic response and recovery

### Scenario 4: Rapid Double Step (Stress Test)
- 1000 -> 200 -> 1000 W/m2
- Purpose: Test algorithm behavior under extreme irradiance drop

### Scenario 5: Temperature Step
- Irradiance: 1000 W/m2 (constant)
- Temperature: 25C -> 50C -> 25C
- Step at t = 1s and t = 3s
- Purpose: Test temperature tracking capability

### Scenario 6: Partial Shading — Simple (2 Local Maxima)
- Configuration: 2 panels in series
- Panel 1: 1000 W/m2, 25C
- Panel 2: 400 W/m2, 25C
- Expected: 2 local maxima (1 global)
- Purpose: Basic global search test

### Scenario 7: Partial Shading — Complex (3+ Local Maxima)
- Configuration: 3 panels in series
- Pattern A: [1000, 800, 600] W/m2 -> 3 local maxima
- Pattern B: [1000, 500, 300] W/m2 -> 3 local maxima, widely spaced
- Pattern C: [1000, 1000, 400] W/m2 -> 2 local maxima
- Purpose: Rigorous global search validation

### Scenario 8: Rapid Fluctuation (Cloud Passage)
- Irradiance profile: Sinusoidal or ramped fluctuation
- Example: 1000 -> 600 -> 800 -> 400 -> 1000 W/m2 over 5 seconds
- Purpose: Simulate realistic cloud passage

### Scenario 9: Sensor Noise Robustness
- Base condition: 1000 W/m2, 25C
- Noise: +/-1% Gaussian noise on V and I measurements
- Duration: 2 seconds
- Purpose: Test algorithm robustness to real-world sensor noise

---

## Metrics (Log Per Run, Per Algorithm, Per Scenario)

### Core Metrics
| Metric | Definition | Unit |
|--------|-----------|------|
| **Tracking efficiency (eta)** | eta = (integral P_actual dt) / (integral P_theoretical_max dt) x 100% | % |
| **Convergence time (t_conv)** | Time to first reach within 2% of MPP | ms or s |
| **Settling time (t_settle)** | Time to stay within 2% of MPP for >=100ms | ms or s |
| **Steady-state oscillation amplitude** | Peak-to-peak power ripple after convergence | W or % of P_MPP |
| **Steady-state oscillation (std)** | Standard deviation of power after convergence | W |

### Energy-Based Metrics (Critical Addition)
| Metric | Definition | Unit |
|--------|-----------|------|
| **Energy yield** | Total energy extracted over scenario duration | Wh or J |
| **Energy yield ratio** | E_actual / E_theoretical_max | % |

### Computational Metrics
| Metric | Definition | Unit |
|--------|-----------|------|
| **Execution time per iteration** | Wall-clock time for one step() call | us or ms |
| **Relative computational burden** | Normalized to P&O baseline | — |

### Statistical Reporting
For Monte Carlo results, report:
- **Mean** +/- **standard deviation**
- **95% confidence interval**
- **Median** and **interquartile range** (if distribution is non-normal)

Use **ANOVA** or **paired t-test** for statistical comparison between algorithms.

---

## Conventions & Standards

### Code Conventions
- Every algorithm module exposes the same interface: step(v, i, duty_cycle) -> new_duty_cycle
- All physical constants/parameters live in config.py, not hardcoded in logic
- Each new algorithm gets a standalone sanity test in tests/ before being added to comparison
- Type hints on all public functions
- Docstrings with Args/Returns/Raises

### Plotting Conventions
- Plots saved as both .png (300 DPI, paper) and .svg (editable vector)
- Use IEEE-compliant color palette (colorblind-friendly)
- Label axes with units: Power (W), Voltage (V), Time (s), Irradiance (W/m2)
- Include error bars or shaded confidence intervals for Monte Carlo results
- Figure captions must be self-contained

### Results Format
- Results tables written to results/comparison_table.csv in **long format**
- Columns: algorithm, scenario, metric, value, run_id, seed
- Enables easy pivoting and statistical analysis

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all sanity tests
pytest tests/ -v --cov=src

# Run full comparison (all scenarios x all algorithms x Monte Carlo)
python -m src.scenarios --monte-carlo 50 --output results/

# Generate figures
python -m src.plotting --input results/comparison_table.csv --output results/figures/

# Compile paper (requires LaTeX)
cd paper && pdflatex main.tex && bibtex main && pdflatex main.tex
```

---

## Status / TODO

### Phase 1: Foundation (Weeks 1-2)
- [x] Lock in reference panel datasheet — **Canadian Solar CS6P-250P** (see PV Model Parameters section)
- [x] Implement two-diode PV model with bypass diodes (`src/pv_model.py`: `TwoDiodeModel`, `PVModuleGroup`/`PVModule`/`PVString` for bypass-diode composition)
- [~] Implement parameter extraction — `extract_two_diode_parameters()` fits Iph/Rs/Rsh/a2 via bounded nonlinear least squares (a1 fixed, Is1=Is2 solved analytically from the Voc condition); this is a documented simplification, not the full Ishaque/Salam/Taheri (2011) iterative procedure — see the docstring's "Citation Flags" note before treating it as final
- [~] Validate simulated I-V/P-V curves against datasheet (RMSE < 2%) — validated against the four STC key points (Voc, Isc, Vmp, Imp) in `tests/test_pv_model.py`, all within 2% (max error 0.068%, at Pmax). The full manufacturer datasheet PDF (`data/panel_datasheet.pdf`) was sourced while scoping Phase 4/5 work — verified authentic (official Canadian Solar branding/contact info/copyright notice, STC values matching `config.py` exactly) and cross-checked against multiple independent distributor mirrors returning identical specs. Ki/Kv/Kp temperature coefficients extracted into `config.py` (`KI_ISC_PCT_PER_C=0.065`, `KV_VOC_PCT_PER_C=-0.34`, `KP_PMAX_PCT_PER_C=-0.43`, NOCT=45±2°C matching `config.NOCT_CELL_TEMPERATURE_C`), so this is no longer blocked on missing data — only on writing the actual NOCT/low-irradiance validation test, which doesn't exist yet. Also surfaced while sourcing this: `pv_model.py`'s `TwoDiodeModel` temperature dependence is currently implicit (via the thermal-voltage term only), not calibrated against these explicit coefficients — whether the two agree quantitatively is exactly what the still-missing NOCT test would check; see `data/README.md`.
- [x] Implement boost converter with state-space averaged model (`src/converter.py`: `design_boost_converter()`, `small_signal_model()` — includes the RHP zero CLAUDE.md's worked equation omits)
- [x] Document converter component sizing with equations (docstrings in `src/converter.py`; worked-example values matched by `tests/test_converter.py`)
- [x] Add DCM check and document implications (`is_discontinuous_conduction()`, `critical_inductance()`; confirmed CCM at full load, DCM at light load in `tests/test_converter.py`; the "document implications" half was added later as a docstring note on `is_discontinuous_conduction()` — in DCM, Vout/Vin depends on L/fs/load rather than just D, so every algorithm's duty-cycle-perturbation reasoning (dP/dV for P&O/IncCond/fuzzy/SMC, reward for Q-learning) sees a non-CCM sensitivity at light load; flagged as a candidate confound to check for in Phase 4's low-irradiance/partial-shading results discussion, not something fixed by algorithm changes)

### Phase 2: Algorithms (Weeks 3-5, extended for 5th algorithm)
- [x] Implement P&O with adaptive step size (`src/algorithms/p_and_o.py`)
- [x] Implement IncCond with boundary condition handling (`src/algorithms/inc_cond.py`)
- [x] Design fuzzy rule base with physical justification per rule (`src/algorithms/fuzzy_logic.py`: the 49-rule 7x7 table is *generated* from a formula — D_level = clip(round(-(E_level+CE_level)/2)) — rather than hand-transcribed, and verified against CLAUDE.md's literal table entry-for-entry in `tests/test_fuzzy_logic.py`; the formula is the physical justification common to all 49 rules, so no rule needs a bespoke citation, but the 7x7 partition size itself still needs a literature citation — see Citation Flags below)
- [x] Implement fuzzy logic with centroid defuzzification (`src/algorithms/fuzzy_logic.py`)
- [x] Implement Q-learning: discretize state space, define reward, build training loop (`src/algorithms/q_learning.py`: (V, dP/dV) discretized to 30x7 bins per CLAUDE.md's suggested ranges; 3 actions mirroring P&O's step; reward = ΔP, not raw P — see note below)
- [x] Train Q-learning on a subset of shading/irradiance profiles; hold out the rest for evaluation — trained on QL_TRAINING_IRRADIANCES = [600, 800, 1000] W/m2, evaluated on held-out 700 W/m2 in `tests/test_q_learning.py::test_generalizes_to_held_out_irradiance`; this is flat-irradiance generalization on a single uniform module, not yet the harder cross-shading-pattern generalization test from CLAUDE.md's Known Risks section, which needs Phase 3's multi-panel scenario definitions
- [x] Implement SMC: choose sliding surface + reaching law, implement chattering mitigation (`src/algorithms/sliding_mode.py`: s=dP/dV; exponential reaching law, ds/dt=-k·sign(s)-q·s (Gao & Hung 1993); sign(s) replaced by a boundary-layer saturation (Slotine & Li 1991) — `tests/test_sliding_mode.py::test_boundary_layer_reduces_chattering_vs_narrow_boundary` empirically confirms shrinking the boundary layer toward pure sign() reproduces the classic chattering problem (0% power ripple at BOUNDARY=0.1 vs. sustained ~2.5% ripple at BOUNDARY=0.001), i.e. the mitigation is verified to actually do its job, not just present)
- [x] Derive and document Lyapunov stability argument for SMC (docstring of `src/algorithms/sliding_mode.py`: V=0.5s², dV/dt=-k|s|-qs²≤0)
- [x] pytest sanity tests for each algorithm (must find MPP at STC) — done for all 5 algorithms (P&O, IncCond, Fuzzy, Q-learning, SMC)
- [x] Sensitivity analysis: test 5x5 and 3x3 fuzzy rule bases — reduced rule bases derived (same generating formula, fewer labels) and verified to find the STC MPP in `tests/test_fuzzy_logic.py`; the full performance-tradeoff comparison was still missing after Phase 3 completed (found while scoping Phase 4 — `results/comparison_table.csv` had 0 `fuzzy_5x5`/`fuzzy_3x3` rows despite this being flagged a "publishable contribution"). Closed in Phase 4 prep: `scenarios.build_fuzzy_rule_base_variants()` + `python -m src.scenarios --fuzzy-variants-only` ran both variants through the full 50-run x 11-scenario sweep and appended their rows. Result at `results/fuzzy_sensitivity_table.csv`: at steady state, fuzzy_5x5 (99.88% tracking efficiency) is statistically indistinguishable from the full 7x7 fuzzy_logic (99.87%) — real support for the "5x5 matches 7x7" contribution CLAUDE.md hoped for; fuzzy_3x3 (99.01%) is measurably lower but still close. See `src/plotting.py`'s `plot_fuzzy_sensitivity()` figure for the full per-scenario comparison.

**Phase 2 status: all 5 algorithms implemented and passing STC sanity tests (47/47 tests, `pytest tests/ -v`).** Remaining Phase 2 item is the fuzzy 5x5/3x3 performance-tradeoff table, which needs Phase 3's scenario/metrics infrastructure to produce real numbers rather than just STC convergence checks.

**Note on SMC citation:** per CLAUDE.md's own caution, no citation was picked before finalizing the design. Utkin (1977) covers general SMC theory, Gao & Hung (1993) is cited for the exponential reaching law specifically, and Slotine & Li (1991) for the boundary-layer method — but the specific PV-SMC paper whose surface/reaching-law combination most closely matches this implementation still needs to be found during the Phase 4 literature review.

**Note on FUZZY_E_SCALE/FUZZY_CE_SCALE (src/config.py):** the initial normalization guess (E_SCALE=10 W/V, matched to dP/dV right at V=0) caused the controller to limit-cycle indefinitely instead of converging — this panel's dP/dV is steeply asymmetric (~+8.9 W/V at V=0 vs. ~-76 W/V approaching Voc), so a gain sized off the small end saturates the fuzzy input too close to the MPP and every correction fires near-maximal. Fixed by grid search to E_SCALE=40, CE_SCALE=1.0, which converges cleanly at STC — but this was tuned against the single STC sanity case, not the full scenario suite, so revisit once Monte Carlo results exist.

**Note on Q-learning reward choice:** CLAUDE.md lists both raw power P(k) and ΔP as acceptable rewards. Raw P(k) was tried first and rejected — it produced a policy permanently stuck 2-3V past the true MPP for some training irradiances, because coarse voltage-bin discretization can keep the operating point in the same state bin for several consecutive steps while it drifts away from the MPP, and a reward tied only to that bin's power level doesn't register the drift. ΔP = P(k)-P(k-1) fixed this by penalizing power-losing actions immediately regardless of bin. Also worth flagging: `simulate.pv_operating_point()` was rewritten to solve the PV-curve/load-line intersection as a single root-find (substituting V=I*R_in directly into the two-diode equation) instead of nesting a full `current_at_voltage` solve inside an outer voltage search — the nested version made Q-learning training (hundreds of thousands of operating-point evaluations) take ~9 minutes; the single-solve version is numerically identical (cross-checked to ~1e-10) and cut that to under a minute.

### Phase 3: Scenarios & Metrics (Weeks 6-7, extended for 5th algorithm)
- [x] Implement all 9 test scenarios (`src/scenarios.py` for the 7 single-module scenarios 1-5/8/9; `src/scenarios_partial_shading.py` for scenarios 6-7 — separate module because partial shading needs a multi-module `PVString` solve and a dense-sweep global-MPP finder instead of the single-module bounded search, since bypass-diode shading is exactly what creates the multiple local maxima a unimodal search would miss)
- [x] Add sensor noise injection (+/-1% Gaussian) (`scenario_sensor_noise_robustness()`, perturbs only the measurements passed to `algorithm.step()`, not the recorded physical power)
- [x] Implement Monte Carlo framework (>=50 runs per pair) (`run_monte_carlo()` / `run_partial_shading_monte_carlo()`; seed = `base_seed + run_id` regardless of algorithm, satisfying "identical random seeds for fair comparison" — verified in `tests/test_scenarios.py::test_run_monte_carlo_uses_identical_seeds_across_algorithms`)
- [x] Profile full sweep runtime early — measured (see note below): **~89 minutes** for the full 5-algorithm x 50-run x 11-scenario sweep (11, not 9, since Scenario 7's three shading patterns are each their own run). Not yet reduced further; flagging for a decision before actually running it for final results, per Known Risks.
- [x] For Q-learning specifically: report train-distribution and held-out results separately — `src/scenarios.py`: `classify_ql_condition()`/`scenario_ql_condition()` add a `ql_condition` column (`"train"` / `"held_out"` / `"not_applicable"`) to every row; a scenario is `"train"` only if every condition it exercises (irradiance, temperature, no sensor noise, single-module topology) matches what `train_q_learning()` actually trained on. Result: q_learning is `"train"` only for `steady_state` and `step_change_irradiance` (both endpoints individually in `QL_TRAINING_IRRADIANCES`), `"held_out"` for the other 9 scenarios (untrained irradiance levels, non-STC temperature, sensor noise, or partial shading's multi-module topology, which was never trained on at all), and `"not_applicable"` for every non-Q-learning row. Deliberately coarse: `step_change_irradiance` is tagged `"train"` even though the mid-run *step* itself was never trained on (training only sees static irradiance per episode) — see the function's docstring caveat. Covered by 12 tests in `tests/test_scenarios.py`. (Note: the tag value is `"not_applicable"`, not the more natural `"n/a"` — pandas' default `read_csv` treats `"n/a"` as a missing-value sentinel and silently coerces it to `NaN`, which would have broken any `df.ql_condition == ...` filter in Phase 4; caught by reading the regenerated CSV back with pandas before trusting it.)
- [x] Add energy yield metrics (`src/metrics.py`: `energy_yield`, `energy_yield_ratio`)
- [x] Add computational burden metrics (`src/metrics.py`: `mean_step_execution_time`, `relative_computational_burden`)
- [x] Run full comparison and generate raw results — `python -m src.scenarios --monte-carlo 50 --output results/` (the `main()` CLI entry point) run to completion: 19,260 rows in `results/comparison_table.csv` (5 algorithms x 11 scenarios x 50 runs, long format, now including `ql_condition`). Row count and `ql_condition` distribution spot-checked with pandas after the run.

**Phase 3 status: complete.** `results/comparison_table.csv` (19,260 rows) is the raw Monte Carlo dataset Phase 4's statistical analysis and figures will consume. 103/103 tests passing (`pytest tests/ -v --cov=src`).

**Runtime profiling note:** partial shading is the dominant cost (~14s per algorithm per run summed across its 4 scenarios, even after amortizing the one-time global-MPP reference sweep over many Monte Carlo runs) because each operating-point solve needs one root-find per bypass-diode group (~9 for a 3-module string) rather than the single-module case's one; `rapid_fluctuation_cloud_passage` is the next largest single-module cost because its continuously-varying irradiance defeats the reference-curve cache that makes the piecewise-constant scenarios cheap. Both are inherent to what those scenarios test, not obviously fixable without changing what's being measured.

### Phase 4: Analysis & Paper (Weeks 8-10)
- [x] Statistical analysis: ANOVA / t-test between algorithms — `src/analysis.py`: `run_anova()` (one-way ANOVA, `scipy.stats.f_oneway`) and `run_pairwise_ttests()` (paired t-test, `scipy.stats.ttest_rel`, paired by `run_id` per the identical-seed Monte Carlo design) over every `(scenario, metric)` combination, restricted by default to the 5 core algorithms (`CORE_ALGORITHMS`) and excluding `_computational_burden` (n=1, not a distribution). Output: `results/statistical_tests.csv` (847 rows: 77 ANOVA + 770 paired t-test). Both explicitly report "insufficient data"/0 usable pairs rather than crashing or silently computing on too-small or all-NaN groups. Note for whoever reads this table next: a handful of near-constant metric groups (e.g. `sensor_noise_robustness`/`oscillation_p2p_w` for algorithms that lock onto the same value every run) trigger scipy `ConstantInputWarning`/precision-loss warnings — not a bug, just means the F/t statistic is close to undefined for that group; check `n_valid` and `std` in `summary_table.csv` before trusting a very large/small p-value in that row.
- [x] Generate all figures (.png + .svg) — `src/plotting.py`: Okabe & Ito (2008) colorblind-safe categorical palette; `plot_metric_comparison()` (tracking efficiency/oscillation/energy-yield-ratio bar charts with 95% CI error bars), `plot_convergence_heatmap()` (algorithm x scenario, `convergence_rate`/`settling_rate` — deliberately **not** `RdYlGn`, a red-green diverging colormap that's exactly the wrong choice for the most common color blindness, caught by visually reviewing the first render; uses `viridis` with value-adaptive text color instead), `plot_computational_burden()`, `plot_ql_train_vs_held_out()`, `plot_fuzzy_sensitivity()`, and `plot_tracking_trajectory()` (the only figure needing a live re-simulation via `scenarios.run_scenario()`/`scenarios_partial_shading.run_partial_shading_scenario()`, since raw per-timestep traces aren't in the summary CSV). `python -m src.plotting --input results/comparison_table.csv --output results/figures/` wrote 10 figures (20 files). Also caught and fixed by visual review: the default `loc="best"` legend placement collided with bar data on several dense charts (most visibly, it sat directly on top of the first bar group in the fuzzy-sensitivity figure) — fixed by anchoring the legend outside the axes unconditionally in `_grouped_bar()`.
- [x] Compile comparison table with confidence intervals — `src/analysis.py`: `summarize()` produces `results/summary_table.csv` (703 rows: per algorithm/scenario/metric[/ql_condition], `n`, `n_valid`, `mean`, `std`, 95% CI (Student's t), `median`, `IQR`). Non-convergence handling (see Known Risks below) required a deliberate design choice: `convergence_time_s`/`settling_time_s` emit an additional derived `convergence_rate`/`settling_rate` row (Wilson-score 95% CI, valid at the p=0/p=1 extremes unlike the naive normal approximation) computed *before* NaN-dropping, so "0 of 50 runs ever converged" shows up as an explicit rate of 0.0 rather than vanishing into a NaN mean.
- [~] Write literature review section — `paper/sections/02_literature_review.tex` organized by the same four paradigms used throughout the paper; 9 of CLAUDE.md's already-named citations independently verified against Crossref metadata (title/authors/journal/volume/pages/DOI all cross-checked; caught one error along the way — Utkin's real title is "...Sliding *Modes*", not "...Sliding Mode Control"), plus 4 real candidate citations found for the two still-open Citation Flags (SMC design match, 7x7 fuzzy partition precedent) and the general 2020-2025 survey landscape — see `paper/references.bib`'s comments for exactly what's verified vs. still needs a full read before citing. Not submission-ready: `publication_supplement.md`'s checklist wants >=20 references (>=15 from 2023-2025); this section has 13 total and is explicitly marked incomplete in its own header comment.
- [~] Write full paper with derivations and justifications — `paper/main.tex` (IEEEtran) + all 8 section files scaffolded and drafted with real prose, not placeholders: PV model/converter/algorithms sections adapted from the actual docstrings in `src/`, and — critically — the Results & Discussion section (`07_results.tex`) pulled every number directly from `results/summary_table.csv`/`statistical_tests.csv`/`fuzzy_sensitivity_table.csv` (steady-state performance table, the 0%-convergence-under-partial-shading finding, the fuzzy 5x5 sensitivity result, computational burden), per RESEARCH_PROGRAM.md's standing rule against fabricated numbers. Manually verified (no `pdflatex` available on this machine to do a real compile): brace/environment balance, every `\cite{}` key resolves in `references.bib`, every `\ref{}`/`\eqref{}` resolves to a real `\label{}`, and all 6 embedded figures exist on disk. Still open: NOCT/low-irradiance validation numbers in `03_pv_model.tex` are explicitly left as pending (not fabricated) since that test doesn't exist yet; the two SMC/fuzzy citation TODOs in the literature review; and an actual `pdflatex`/`bibtex` compile check once LaTeX is available.
- [~] Open-source release: GitHub + Zenodo DOI — `CITATION.cff` added (no ORCID — left blank rather than a placeholder that could be mistaken for real); README.md's stale "Phase 1 in progress" status line and reproduction steps fixed. Still the user's manual follow-up: enabling Zenodo-GitHub integration (needs their Zenodo login), tagging/pushing `v1.0.0-ieee-submission`, and adding the DOI badge once Zenodo mints it.
- [ ] Preprint on TechRxiv or arXiv
- [ ] Submit to target IEEE journal

**Phase 4 analysis/figures status: complete.** `pytest tests/ -v --cov=src` at 125/125. Headline findings the statistical/figure pipeline surfaced, worth carrying into the paper's Results & Discussion:
- **Partial shading defeats every algorithm's global search except in the mildest pattern.** `convergence_rate` is **0%** for all 5 core algorithms (P&O, IncCond, fuzzy_logic, SMC, and even Q-learning) on `partial_shading_simple`, `_pattern_a`, and `_pattern_b` — none of them find the true global MPP within 2% in any of 50 runs. Only `_pattern_c` (2 local maxima, the mildest of the 4 shading configurations) shows partial success (`inc_cond` 44%, `q_learning` 98%, others 100%). `plot_tracking_trajectory`'s `partial_shading_simple` illustration shows *why*: P&O/IncCond/fuzzy/SMC all converge to the same local maximum (~193W vs. a true ~207W), while untrained Q-learning does something qualitatively worse — it moves to a low-power point (~114W) and oscillates there, rather than just getting stuck.
- **Q-learning's own training-distribution scenario isn't fully solved either**: `convergence_rate` is 80% (40/50), not 100%, at `steady_state` — worth flagging alongside the held-out numbers rather than only reporting the held-out generalization gap.
- **Fuzzy rule-base reduction genuinely works**: 5x5 (99.88%) is statistically indistinguishable from 7x7 (99.87%) tracking efficiency at steady state — see the Phase 2 sensitivity-analysis note above.
- **Fuzzy logic is ~100x P&O's computational cost** (Mamdani inference + centroid defuzzification over a 201-point grid); Q-learning is ~11x (table lookup, but with per-step numpy overhead); IncCond and SMC are close to P&O's baseline.

---

## Notes for Claude

### Priority: Correctness Over Speed
This is a research simulation, not production code. Prioritize:
1. Physically accurate two-diode model with bypass diodes
2. Rigorous model validation against datasheet
3. Statistical rigor (Monte Carlo, confidence intervals)
4. Reproducibility (locked dependencies, CI, open source)

### Fuzzy Logic Documentation
When implementing fuzzy logic, **comment the reasoning behind each rule** so it's easy to lift directly into the paper's methodology section. Each rule should have a one-line physical justification.

### Citation Flags
Flag any design choice that needs a citation or justification for the paper. Do not silently assume. Key flags:

| Design Choice | Needs Citation | Suggested Source |
|--------------|----------------|-----------------|
| Two-diode vs. single-diode model | **Yes — mandatory** | Ishaque, Salam & Taheri 2011 |
| Bypass diode configuration | Yes | Standard PV module practice |
| Boost converter inductor ripple (30%) | Yes | Erickson & Maksimovic, Fundamentals of Power Electronics |
| Fuzzy 7 MFs x 7 MFs | Yes | Precedent in literature |
| Fuzzy rule base design | **Yes — each rule** | Derive from physical MPP behavior |
| P&O adaptive step size | Yes | Femia et al. 2005 |
| Q-learning state/action/reward design | **Yes — mandatory** | Kofinas et al. 2017 |
| Q-learning train/test split methodology | **Yes — mandatory** | Standard ML practice; cite a generalization/overfitting reference, not just RL-MPPT papers |
| SMC sliding surface + reaching law choice | **Yes — mandatory** | Utkin 1977 (theory) + specific PV-SMC paper matching your exact design (pick after finalizing design, see Algorithms section) |
| SMC chattering mitigation method | Yes | Cite whichever boundary-layer/sigmoid approach you adopt |
| 2% convergence threshold | Yes | Common in MPPT literature |
| Partial shading patterns | Yes | Standard test patterns from literature |
| Monte Carlo sample size (>=50) | Yes | Statistical power justification |

### Target Journals (Ranked by Fit)
1. **IEEE Transactions on Energy Conversion** — Best fit for simulation-only with rigorous model validation
2. **IEEE Journal of Photovoltaics** — Strong fit for PV-focused work
3. **IEEE Transactions on Industrial Electronics** — High bar, may require experimental validation
4. **IEEE Access** — Lower bar, faster review, open access — good for reproducibility-focused work
5. **IET Renewable Power Generation** — Alternative, slightly lower novelty bar

### Open-Source Strategy
- Release code on GitHub with MIT/BSD-3 license
- Archive on Zenodo with DOI for citation in paper
- Include Binder badge for interactive notebooks
- Tag release: v1.0.0-ieee-submission

### Paper Structure (IEEEtran, double-column)
1. **Introduction** — Problem, motivation, contributions (highlight reproducibility + cross-paradigm framing — state explicitly that this avoids the saturated "one more optimizer" pattern)
2. **Literature Review** — Survey organized by paradigm: perturbative (P&O, IncCond), rule-based (fuzzy), learning-based (RL/Q-learning), model-based control (SMC) — this structure itself supports the novelty argument
3. **PV System Modeling** — Two-diode model, parameter extraction, bypass diodes, validation
4. **Boost Converter Modeling** — State-space model, component sizing, DCM check
5. **MPPT Algorithms** — Unified framework, all 5 algorithm descriptions, fuzzy rule justification, Q-learning training protocol, SMC stability proof
6. **Test Scenarios & Metrics** — Scenario definitions, Monte Carlo methodology, train/test split for Q-learning
7. **Results & Discussion** — Tables with confidence intervals, figures, statistical tests
8. **Conclusion** — Summary, limitations, future work

### Known Risks
- **Novelty risk:** P&O vs. IncCond vs. Fuzzy is saturated, and so is "yet another bio-inspired optimizer." Mitigated by spanning four genuinely different paradigms (perturbative/rule-based/learning-based/model-based-control) plus open-source + statistical rigor — but this framing needs to be explicit in the Introduction, not left implicit
- **Q-learning generalization risk:** if train/test evaluation isn't kept separate and reported separately, a reviewer will (rightly) ask whether the policy just memorized the training shading patterns. Build this split in from the start, not retrofitted before submission
- **SMC chattering risk:** unmitigated chattering shows up clearly in your oscillation-amplitude metric and will look bad next to P&O in that one column even if SMC wins elsewhere. Implement and validate the boundary-layer/sigmoid mitigation before running the full comparison, not after
- **Experimental validation risk:** Some IEEE TIE reviewers may reject without hardware. Mitigate by targeting IEEE TEC or JPV, or adding simple hardware validation as future work
- **Model validation risk:** If simulated curves don't match datasheet, entire paper is invalidated. Spend extra time on parameter extraction
- **Scope risk (5 algorithms, not 3):** each additional algorithm multiplies your Monte Carlo runtime across 9 scenarios. Profile early — if wall-clock time for the full sweep is unreasonable, consider reducing to the scenarios that most differentiate the algorithms rather than cutting an algorithm
