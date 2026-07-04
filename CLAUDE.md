# MPPT Algorithm Comparison — IEEE Journal Publication Plan

**Companion document:** `publication_supplement.md` — IEEE submission checklists, templates,
and reproduction-package guidance. If algorithm set, panel choice, or target journal change
here, re-check that file for stale references (it has drifted out of sync before).

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
├── claude.md                  # This file
└── publication_supplement.md  # Companion: IEEE submission checklists & templates
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
- [~] Validate simulated I-V/P-V curves against datasheet (RMSE < 2%) — validated against the four STC key points (Voc, Isc, Vmp, Imp) in `tests/test_pv_model.py`, all within 2%; NOCT and low-irradiance curve validation still blocked on the full datasheet PDF (see `data/README.md`)
- [x] Implement boost converter with state-space averaged model (`src/converter.py`: `design_boost_converter()`, `small_signal_model()` — includes the RHP zero CLAUDE.md's worked equation omits)
- [x] Document converter component sizing with equations (docstrings in `src/converter.py`; worked-example values matched by `tests/test_converter.py`)
- [x] Add DCM check and document implications (`is_discontinuous_conduction()`, `critical_inductance()`; confirmed CCM at full load, DCM at light load in `tests/test_converter.py`)

### Phase 2: Algorithms (Weeks 3-5, extended for 5th algorithm)
- [x] Implement P&O with adaptive step size (`src/algorithms/p_and_o.py`)
- [x] Implement IncCond with boundary condition handling (`src/algorithms/inc_cond.py`)
- [ ] Design fuzzy rule base with physical justification per rule
- [ ] Implement fuzzy logic with centroid defuzzification
- [ ] Implement Q-learning: discretize state space, define reward, build training loop
- [ ] Train Q-learning on a subset of shading/irradiance profiles; hold out the rest for evaluation
- [ ] Implement SMC: choose sliding surface + reaching law, implement chattering mitigation
- [ ] Derive and document Lyapunov stability argument for SMC
- [~] pytest sanity tests for each algorithm (must find MPP at STC) — done for P&O and IncCond (`tests/test_p_and_o.py`, `tests/test_inc_cond.py`, backed by the new `src/simulate.py` steady-state PV/converter solver); still needed for fuzzy, Q-learning, SMC
- [ ] Sensitivity analysis: test 5x5 and 3x3 fuzzy rule bases

### Phase 3: Scenarios & Metrics (Weeks 6-7, extended for 5th algorithm)
- [ ] Implement all 9 test scenarios
- [ ] Add sensor noise injection (+/-1% Gaussian)
- [ ] Implement Monte Carlo framework (>=50 runs per pair)
- [ ] Profile full sweep runtime early (5 algorithms x 9 scenarios x 50 runs) — adjust scenario count if wall-clock time is unreasonable, per Known Risks
- [ ] For Q-learning specifically: report train-distribution and held-out results separately
- [ ] Add energy yield metrics
- [ ] Add computational burden metrics
- [ ] Run full comparison and generate raw results

### Phase 4: Analysis & Paper (Weeks 8-10)
- [ ] Statistical analysis: ANOVA / t-test between algorithms
- [ ] Generate all figures (.png + .svg)
- [ ] Compile comparison table with confidence intervals
- [ ] Write literature review section
- [ ] Write full paper with derivations and justifications
- [ ] Open-source release: GitHub + Zenodo DOI
- [ ] Preprint on TechRxiv or arXiv
- [ ] Submit to target IEEE journal

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
