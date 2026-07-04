# Publication Supplement — IEEE Journal Submission Package

Companion document to `CLAUDE.md`. Contains checklists, templates, and guidance for preparing the full IEEE submission package including supplementary materials, response letters, and reproduction artifacts.

**Sync note:** this document has been updated to match the current project state —
5 algorithms (P&O, IncCond, Fuzzy, Q-learning, SMC) across 4 paradigms, Canadian
Solar CS6P-250P reference panel, corrected two-diode citation. If `CLAUDE.md`
changes again (algorithm set, panel choice, target journal), re-check this file
for the same stale-reference problem it had before this pass.

---

## Table of Contents
1. [IEEE Submission Checklist](#1-ieee-submission-checklist)
2. [Supplementary Materials](#2-supplementary-materials)
3. [Reproduction Package](#3-reproduction-package)
4. [Reviewer Response Templates](#4-reviewer-response-templates)
5. [Ethics & Data Availability Statements](#5-ethics--data-availability-statements)
6. [Author Contribution Statement](#6-author-contribution-statement)
7. [Conflict of Interest Declaration](#7-conflict-of-interest-declaration)
8. [Cover Letter Template](#8-cover-letter-template)
9. [Response to Reviewers Template](#9-response-to-reviewers-template)
10. [Revision Log Template](#10-revision-log-template)

---

## 1. IEEE Submission Checklist

### Pre-Submission (Complete ALL before clicking Submit)

#### Manuscript
- [ ] IEEEtran LaTeX class used (double-column, 10pt)
- [ ] Paper length within journal limits (typically 8-14 pages for TEC/JPV)
- [ ] All figures are vector (.eps/.pdf) or 300+ DPI raster (.png/.tiff)
- [ ] All equations numbered and referenced
- [ ] All tables use booktabs-style formatting (no vertical rules)
- [ ] All acronyms defined on first use
- [ ] Abstract: 150-250 words, standalone, no citations
- [ ] Keywords: 4-6 IEEE Index Terms
- [ ] Introduction clearly states contributions and novelty
- [ ] Literature review positions work against 20+ recent papers (2020-2025)
- [ ] All citations use IEEE format: [1] numbered, in order of appearance
- [ ] DOI included for all references where available
- [ ] No self-plagiarism from prior publications
- [ ] Grammar checked (Grammarly / LanguageTool / native speaker review)

#### Figures & Tables
- [ ] Figure 1: System block diagram (PV array -> boost converter -> load + MPPT controller)
- [ ] Figure 2: Two-diode model equivalent circuit
- [ ] Figure 3: Simulated vs. datasheet I-V and P-V curves (with RMSE annotation)
- [ ] Figure 4: Boost converter topology with labeled components
- [ ] Figure 5: Fuzzy membership functions (7 sets, 3 plots: E, delta_E, delta_D)
- [ ] Figure 6: Fuzzy rule base surface plot or heatmap
- [ ] Figure 7: Scenario 3 (step-change) power vs. time for all 5 algorithms
- [ ] Figure 8: Scenario 7 (complex partial shading) P-V trajectory for all 5 algorithms
- [ ] Figure 9: Convergence time comparison (bar chart with error bars)
- [ ] Figure 10: Tracking efficiency comparison (bar chart with error bars)
- [ ] Figure 11: Steady-state oscillation amplitude comparison
- [ ] Figure 12: Energy yield ratio comparison
- [ ] Figure 13: Computational burden comparison
- [ ] Figure 14: Q-learning training curve (reward vs. episode) + train-vs-held-out performance
- [ ] Figure 15: SMC phase portrait or chattering illustration (with/without boundary-layer mitigation)
- [ ] Table I: Reference panel datasheet parameters
- [ ] Table II: Boost converter component values and design equations
- [ ] Table III: Fuzzy rule base (7x7, formatted for IEEE)
- [ ] Table IV: Scenario definitions summary
- [ ] Table V: Monte Carlo statistical results (mean +/- std, 95% CI)
- [ ] Table VI: ANOVA / t-test p-values for algorithm comparisons
- [ ] Table VII: Sensitivity analysis: fuzzy rule base reduction results

#### Mathematical Content
- [ ] Two-diode model equations fully derived and numbered
- [ ] Parameter extraction method described with algorithm steps
- [ ] Boost converter state-space equations derived
- [ ] Small-signal transfer function derived (optional but strengthens paper)
- [ ] P&O algorithm pseudocode or flowchart
- [ ] IncCond algorithm pseudocode or flowchart
- [ ] Fuzzy logic algorithm pseudocode or flowchart
- [ ] Q-learning MDP formalization: state/action/reward definitions, training protocol, train/held-out split
- [ ] SMC sliding surface, reaching law, and Lyapunov stability proof (V = 0.5*s^2, dV/dt < 0)

#### References
- [ ] >= 40 references total
- [ ] >= 60% from IEEE journals (Transactions, Letters, Magazine)
- [ ] >= 15 from 2023-2025 (demonstrates awareness of recent work)
- [ ] Key foundational papers cited: Femia 2005 (P&O), Ishaque/Salam/Taheri 2011 (two-diode model), Hussein 1995 (rapidly-changing conditions), Kofinas et al. 2017 (Q-learning MPPT), Utkin 1977 (SMC theory) — do NOT cite Villalva 2009 for the two-diode model; that paper's contribution is the single-diode 3-point extraction method
- [ ] No predatory journal citations
- [ ] All DOIs verified and clickable

### Submission Portal (IEEE ScholarOne Manuscripts)
- [ ] Cover letter uploaded (PDF)
- [ ] Manuscript uploaded (PDF + source files)
- [ ] Supplementary materials uploaded (ZIP with code + data)
- [ ] Author ORCIDs linked
- [ ] Corresponding author designated
- [ ] Suggested reviewers: 3-5 names with emails and affiliations
- [ ] Opposed reviewers: listed if any conflicts exist
- [ ] Funding sources declared
- [ ] Open access option selected (if applicable)

---

## 2. Supplementary Materials

### Required Files (ZIP: `supplementary_materials.zip`)

```
supplementary_materials/
├── README_SUPPLEMENT.md       # Guide to supplementary contents
├── code/
│   ├── src/                   # Full source code (mirror of repo)
│   ├── requirements.txt       # Pinned dependencies
│   ├── pyproject.toml         # Package metadata
│   └── README_CODE.md         # Installation and usage instructions
├── data/
│   ├── panel_datasheet.pdf    # Reference panel full datasheet
│   ├── extracted_parameters/  # Parameter extraction results (JSON/CSV)
│   └── validation_curves/     # Simulated vs. datasheet comparison data
├── results/
│   ├── comparison_table.csv   # Long-format results (algorithm, scenario, metric, value)
│   ├── monte_carlo/           # Per-run raw data (50+ runs x 5 algorithms x 9 scenarios)
│   └── figures/               # High-resolution .png and .svg versions
├── notebooks/
│   ├── 01_pv_model_validation.ipynb
│   ├── 02_converter_design.ipynb
│   ├── 03_algorithm_comparison.ipynb
│   └── 04_partial_shading_analysis.ipynb
└── reproduction/
    ├── REPRODUCTION_GUIDE.md  # Step-by-step reproduction instructions
    ├── expected_outputs/      # Expected test outputs for validation
    └── docker/
        ├── Dockerfile         # Containerized environment
        └── docker-compose.yml # One-command reproduction
```

### README_SUPPLEMENT.md Template

```markdown
# Supplementary Materials for "[Paper Title]"

## Contents
This supplementary package contains:
1. Full simulation source code (Python 3.11+)
2. Reference panel datasheet and extracted parameters
3. All raw simulation results (Monte Carlo: 50 runs x 5 algorithms x 9 scenarios)
4. Jupyter notebooks reproducing all figures and tables
5. Docker container for fully reproducible execution

## Quick Start
```bash
# Option 1: Local installation
pip install -r code/requirements.txt
cd code && pytest tests/ -v

# Option 2: Docker (guaranteed reproduction)
cd reproduction/docker
docker-compose up
```

## Code License
MIT License — see code/LICENSE

## Data Availability
All data generated during this study are included in this supplementary package.
No external proprietary datasets were used.

## Contact
[Corresponding Author Name]
[Email]
[Institution]
```

### Docker Environment (Critical for Reproducibility)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY code/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY code/ .
COPY data/ ./data/
COPY results/ ./results/

CMD ["pytest", "tests/", "-v"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  mppt-simulation:
    build: .
    volumes:
      - ./results:/app/output
    command: >
      bash -c "python -m src.scenarios --monte-carlo 50 --output /app/output/ &&
               python -m src.plotting --input /app/output/comparison_table.csv --output /app/output/figures/"
```

---

## 3. Reproduction Package

### Zenodo Archive Checklist
- [ ] GitHub repository public and well-documented
- [ ] Zenodo integration enabled (auto-DOI on release)
- [ ] Release tagged: `v1.0.0-ieee-submission`
- [ ] CITATION.cff file included
- [ ] LICENSE file included (MIT or BSD-3 recommended)
- [ ] README.md with badges: build status, coverage, Zenodo DOI, Binder

### CITATION.cff Template

```yaml
cff-version: 1.2.0
message: "If you use this software, please cite both the software and the paper."
type: software
title: "MPPT Algorithm Comparison: A Reproducible Open-Source Framework"
authors:
  - family-names: "[Last Name]"
    given-names: "[First Name]"
    orcid: "https://orcid.org/0000-0000-0000-0000"
repository-code: "https://github.com/[username]/mppt-comparison"
license: MIT
version: 1.0.0
 date-released: 2025-XX-XX
```

### Binder Configuration
Create `binder/` directory in repo:
```
binder/
├── requirements.txt    # Same as root requirements.txt
└── postBuild           # Optional: pre-run notebooks
```

Add badge to README:
```markdown
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/[username]/mppt-comparison/main)
```

---

## 4. Reviewer Response Templates

### Common Reviewer Comments & Pre-Planned Responses

#### Comment A: "What is the novelty? P&O vs. IncCond vs. Fuzzy has been done many times."
**Pre-planned response:**
> We acknowledge that individual comparisons of these algorithms exist in literature, and that "propose another bio-inspired optimizer" has become a saturated pattern in this space. This work instead makes four distinct contributions beyond prior art:
> 1. **Reproducibility:** We provide the first fully open-source, pure-Python implementation with locked dependencies, CI testing, and containerized reproduction. Most prior work uses MATLAB/Simulink, which reviewers cannot easily reproduce.
> 2. **Rigorous model validation:** Our two-diode model with bypass diodes is quantitatively validated against a real commercial panel datasheet (RMSE: [fill in from actual validation run]). Many prior simulations use generic or unvalidated models.
> 3. **Statistical rigor:** We report Monte Carlo results (50+ runs) with confidence intervals and ANOVA testing, rather than single-run comparisons common in prior work.
> 4. **Cross-paradigm comparison, not variations on one idea:** Rather than adding a fifth flavor of perturbative or swarm-based search, we compare across four genuinely distinct MPPT design paradigms — perturbative (P&O, IncCond), rule-based (Fuzzy Logic), learning-based (Q-learning), and model-based nonlinear control (SMC, with a Lyapunov stability guarantee).
> We have clarified these contributions in the revised Introduction (Section I) and added a dedicated "Contributions" subsection.

#### Comment B: "Why no experimental validation?"
**Pre-planned response:**
> We agree that hardware validation strengthens MPPT studies. However, IEEE Transactions on Energy Conversion and IEEE Journal of Photovoltaics explicitly accept rigorous simulation-only studies when models are validated against manufacturer datasheets and statistical methods are employed (see [cite relevant TEC/JPV papers]). Our two-diode model achieves RMSE = [fill in from actual validation run — target < 2%] against the Canadian Solar CS6P-250P datasheet, meeting this standard. We have added hardware validation as explicit future work in Section VIII and included a discussion of simulation-to-hardware translation challenges.

#### Comment C: "The partial shading scenarios are too simple."
**Pre-planned response:**
> We have expanded the partial shading test suite from 1 scenario (2 panels, 2 maxima) to 3 complex scenarios (3 panels, 3 maxima) with varying shading patterns: [1000, 800, 600], [1000, 500, 300], and [1000, 1000, 400] W/m2. These patterns produce 2-3 local maxima with different spacing, rigorously testing global search capability. See revised Section VI and new Figure 8.

#### Comment D: "Why use a two-diode model instead of single-diode?"
**Pre-planned response:**
> The single-diode model cannot accurately capture the multiple local maxima characteristic of partial shading with bypass diodes. The two-diode model better represents recombination currents at low voltages, which is critical for distinguishing local from global peaks. We have added a comparative analysis in Section III showing that the single-diode model underestimates the number of local maxima by [fill in from actual comparison run] in our test scenarios. Citation: Ishaque, Salam & Taheri (2011) — NOT Villalva et al. (2009), whose contribution is the single-diode 3-point extraction method and should not be cited here.

#### Comment E: "The fuzzy rule base seems arbitrary."
**Pre-planned response:**
> Each of the 49 rules is now physically justified in Table III and Section V-C. For example, Rule 1 (E=NB, delta_E=NB -> delta_D=PB) is justified as: "Operating point is far below MPP and moving away; large positive duty step needed." We have also added a sensitivity analysis (Table VII) showing that a reduced 5x5 rule base (25 rules) achieves [fill in from actual sensitivity run]% of the performance with 50% fewer computations, demonstrating that the rule base is not overfitted.

#### Comment F: "Why only 50 Monte Carlo runs?"
**Pre-planned response:**
> We performed a power analysis to determine the minimum sample size needed to detect a 5% difference in tracking efficiency with 80% power at alpha=0.05. This analysis indicated n=[fill in from actual power analysis] runs. We used n=50 to provide a safety margin. The resulting 95% confidence intervals are sufficiently narrow (typically +/- [fill in]% on efficiency) to distinguish algorithm performance. We have added this power analysis to Section VI.

#### Comment G: "How do you know the Q-learning agent isn't just memorizing the training shading patterns?"
**Pre-planned response:**
> We evaluate Q-learning performance separately on the shading patterns used during training and on a held-out set not seen during training (see Section VI, Table [X]). We report both figures explicitly rather than a single pooled number, so the reader can assess generalization directly. [Fill in actual train vs. held-out performance gap once measured.]

---

## 5. Ethics & Data Availability Statements

### IEEE Required Statements

#### Data Availability Statement (for manuscript)
> The simulation code, raw results data, and parameter extraction outputs are available in the supplementary materials and at [Zenodo DOI link] and [GitHub repository link]. The reference panel datasheet (Canadian Solar CS6P-250P) is publicly available from the manufacturer. No proprietary or restricted datasets were used.

#### Code Availability Statement
> All simulation code is released under the MIT License at [GitHub link] and archived at [Zenodo DOI]. The code includes a Docker container for fully reproducible execution. Installation instructions and expected outputs are provided in the repository README.

#### Funding Statement
> This work was supported by [Funding Agency] under Grant [Number]. [If no funding: "This research received no external funding."]

#### Competing Interests Statement
> The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

---

## 6. Author Contribution Statement

### CRediT Taxonomy Format (IEEE Preferred)

| Author | Conceptualization | Methodology | Software | Validation | Formal Analysis | Investigation | Writing — Original Draft | Writing — Review & Editing | Visualization |
|--------|-------------------|-------------|----------|------------|-----------------|---------------|--------------------------|---------------------------|---------------|
| A. Author | X | X | | X | | X | X | X | |
| B. Author | | X | X | X | X | | | X | X |
| C. Author | | | | | X | | | X | |

*X = primary contribution; (X) = supporting contribution*

### Text Version for Manuscript
> **Author Contributions:** A. Author: conceptualization, methodology, validation, investigation, writing — original draft, writing — review & editing. B. Author: methodology, software, validation, formal analysis, visualization, writing — review & editing. C. Author: formal analysis, writing — review & editing.

---

## 7. Conflict of Interest Declaration

### Template for All Authors

```
Conflict of Interest Declaration

I, [Full Name], declare that:
1. I have no financial interests (stock ownership, patents, royalties) related to the content of this manuscript.
2. I have no personal relationships that could influence this work.
3. I have no employment or consultancy relationships that create a conflict.
4. I have no funding sources beyond those disclosed in the manuscript.

Signed: _________________  Date: _________________
```

---

## 8. Cover Letter Template

```
[Date]

Editor-in-Chief
IEEE Transactions on Energy Conversion
[or: IEEE Journal of Photovoltaics]

Dear Editor,

We wish to submit our manuscript entitled "A Reproducible Open-Source Framework 
for Comparative MPPT Evaluation Across Perturbative, Rule-Based, Learning-Based, 
and Model-Based Control Paradigms Under Partial Shading" [working title — trim 
once you've checked the journal's title-length conventions] for consideration 
for publication in IEEE Transactions on Energy Conversion.

This work addresses a critical gap in Maximum Power Point Tracking (MPPT) 
literature: while hundreds of papers compare P&O, IncCond, and fuzzy logic 
algorithms — and a growing number add yet another bio-inspired swarm optimizer — 
virtually none provide reproducible, open-source implementations that reviewers 
and readers can independently verify, and few span genuinely different MPPT 
design paradigms rather than variations on perturbative search. We present:

1. A rigorously validated two-diode PV model with bypass diodes, quantitatively 
   matched to a commercial Canadian Solar CS6P-250P panel (RMSE: [fill in from 
   actual validation run]).
2. A unified, extensible Python framework for MPPT algorithm comparison, 
   released under MIT License with containerized reproduction via Docker.
3. Monte Carlo statistical analysis (50+ runs) with confidence intervals and 
   ANOVA testing — a level of rigor rarely seen in MPPT comparison studies.
4. A 5-algorithm comparison spanning four distinct paradigms: perturbative 
   (P&O, IncCond), rule-based (Fuzzy Logic), learning-based (Q-learning, 
   evaluated on both training-distribution and held-out shading patterns), 
   and model-based nonlinear control (Sliding Mode Control, with a Lyapunov 
   stability guarantee).

Our simulation results demonstrate that [key finding 1] and [key finding 2], 
with statistical significance (p < 0.05). The open-source release ensures 
full reproducibility and enables the research community to extend this work.

We believe this manuscript aligns with IEEE TEC's scope in power electronics 
modeling and renewable energy systems, and meets the journal's standards for 
rigorous simulation-based studies with validated models.

We confirm that this work is original, has not been published elsewhere, and 
is not under consideration by another journal. All authors have approved the 
manuscript and agree to its submission.

Suggested reviewers:
1. Prof. [Name], [University], [Email] — Expert in MPPT algorithms
2. Dr. [Name], [Institution], [Email] — Expert in PV system modeling
3. Prof. [Name], [University], [Email] — Expert in power electronics simulation

We have no conflicts of interest to declare.

Thank you for your consideration.

Sincerely,

[Corresponding Author Name]
[Title]
[Institution]
[Email]
[ORCID]
```

---

## 9. Response to Reviewers Template

### Structure

```
Response to Reviewers
Manuscript: [ID] — "[Title]"

We thank the Editor and Reviewers for their constructive feedback. We have 
addressed all comments as detailed below. Changes are highlighted in blue 
in the revised manuscript.

---

## Reviewer 1

### Comment 1.1: [Brief summary of comment]
> [Quote reviewer comment verbatim]

**Response:** [Detailed response addressing the concern]

**Action:** [Specific changes made, with line/page numbers]
- Revised Section X, page Y, lines Z-Z: [description of change]
- Added Figure X: [description]
- Added Table X: [description]

### Comment 1.2: [Next comment]
...

---

## Reviewer 2

### Comment 2.1: [Brief summary]
...

---

## Reviewer 3

### Comment 3.1: [Brief summary]
...

---

## Additional Changes Not Triggered by Reviewer Comments

- [List any improvements made proactively]
- [e.g., "Updated all figures to use colorblind-friendly palette"]
- [e.g., "Added convergence analysis for PSO-FLC hyperparameters"]
```

### Response Style Guidelines
- **Always thank the reviewer** — even for harsh comments
- **Never be defensive** — acknowledge limitations honestly
- **Be specific** — cite exact line numbers and quote changes
- **Show evidence** — include new figures/tables in response letter
- **Color-code changes** in revised manuscript (blue for additions, red for deletions)

---

## 10. Revision Log Template

Track ALL changes during revision rounds:

```
Revision Log — Manuscript [ID]

### Round 1 (Initial Submission -> Major Revision)
| Date | Change | Trigger | Section | Status |
|------|--------|---------|---------|--------|
| 2025-XX-XX | Added 2-diode model derivation | Reviewer 1.3 | III-A | Done |
| 2025-XX-XX | Expanded partial shading to 3 scenarios | Reviewer 2.5 | VI | Done |
| 2025-XX-XX | Added power analysis for n=50 | Reviewer 3.2 | VI-B | Done |
| 2025-XX-XX | Fixed typo in Eq. (12) | Self-review | IV | Done |

### Round 2 (Major Revision -> Minor Revision)
| Date | Change | Trigger | Section | Status |
|------|--------|---------|---------|--------|
| ... | ... | ... | ... | ... |

### Round 3 (Minor Revision -> Accept)
| Date | Change | Trigger | Section | Status |
|------|--------|---------|---------|--------|
| ... | ... | ... | ... | ... |
```

---

## Appendix A: IEEE Journal-Specific Notes

**Caveat on acceptance-rate figures below:** IEEE does not consistently publish
exact acceptance rates per journal, so the percentages in this section are rough
estimates, not verified figures — treat them as directional only, not something
to cite or rely on for planning. The APC (open-access fee) and page-limit figures
have been checked against IEEE's official 2026 rate list and are current as of
this writing.

### IEEE Transactions on Energy Conversion (TEC)
- **Scope:** Electric machines, drives, power electronics, renewable energy systems
- **Submission length limit:** 10 pages at first submission — papers exceeding this are returned without review. Revised (R&R) submissions may exceed 10 pages. Overlength charge: $250/page beyond the first 12 published pages (for papers submitted 2024 or later)
- **Open access fee (2026, verified):** $2,800 USD
- **Review time:** IEEE PES targets 3 months for first-round review
- **Acceptance rate:** not publicly verified — treat any specific figure with skepticism
- **Special requirements:** Emphasis on analytical rigor; experimental validation preferred but not mandatory for simulation papers with validated models

### IEEE Journal of Photovoltaics (JPV)
- **Scope:** PV materials, devices, systems, and applications
- **Typical length:** 6-10 pages
- **Open access option:** Yes — check current IEEE APC list for exact fee at submission time
- **Review time:** 1-3 months first round (unverified — confirm on journal site before relying on this)
- **Acceptance rate:** not publicly verified — treat any specific figure with skepticism
- **Special requirements:** Strong preference for real panel data; model validation against datasheet is expected

### IEEE Transactions on Industrial Electronics (TIE)
- **Scope:** Industrial applications of electronics, control, communications
- **Typical length:** 10-14 pages
- **Open access fee:** check current IEEE APC list at submission time (hybrid-journal rate, likely similar to TEC's $2,800)
- **Review time:** 3-6 months first round (unverified)
- **Acceptance rate:** not publicly verified — treat any specific figure with skepticism
- **Special requirements:** Very high bar; experimental validation strongly preferred; simulation-only must be exceptionally rigorous

### IEEE Access
- **Scope:** Multidisciplinary, rapid publication
- **Typical length:** no page limit (recommend staying under ~20 pages for readability); no overlength charges
- **Article processing charge (2026, verified):** $2,160 USD (this replaces the older $1,850 figure, which is now outdated)
- **Review time:** roughly 3-6 weeks for papers moving smoothly through review
- **Acceptance rate:** not publicly verified — treat any specific figure with skepticism
- **Special requirements:** Less stringent novelty requirement; good fit for reproducibility-focused work

---

## Appendix B: Common IEEE Formatting Pitfalls

| Pitfall | Correct Approach |
|---------|-----------------|
| "Fig." vs "Figure" | Use "Fig." in text, "Figure" at sentence start |
| "Table" abbreviation | Never abbreviate — always "Table I" |
| Equation punctuation | End equations with comma/period if they end a sentence |
| Units | Use SI units, space between number and unit: "250 W" not "250W" |
| Acronyms | Define on first use: "Maximum Power Point Tracking (MPPT)" |
| References | No "et al." in reference list — list all authors up to 6, then "et al." |
| Figure captions | Self-contained: "Fig. 1. System block diagram showing..." |
| Table captions | Above table: "TABLE I. BOOST CONVERTER PARAMETERS" |
| Subfigures | Use (a), (b), (c) with sub-captions |
| Color figures | Ensure readability in grayscale (use patterns/line styles) |

---

## Appendix C: Pre-Submission Self-Assessment Scorecard

Rate each item 1-5 (1=poor, 5=excellent). Target: >=4 on all items.

| Criterion | Score | Evidence |
|-----------|-------|----------|
| Novelty clearly stated | | Introduction has explicit contribution list |
| Model validated quantitatively | | RMSE < 2% against datasheet |
| Statistical rigor | | Monte Carlo, CI, ANOVA |
| Reproducibility | | Open source, Docker, CI |
| Literature review depth | | >=20 recent papers (2020-2025) |
| Algorithm descriptions | | Pseudocode/flowcharts for all 5; MDP formalization for Q-learning; Lyapunov proof for SMC |
| Scenario coverage | | >=9 scenarios including noise |
| Figure quality | | Vector formats, 300 DPI, colorblind-safe |
| Table clarity | | booktabs style, no vertical rules |
| Mathematical correctness | | All equations derived and numbered |
| Writing quality | | Grammarly score > 90, native review |
| Citation completeness | | >=40 refs, >=60% IEEE, DOIs verified |

**Total: ___ / 60**

**Threshold for submission:** >= 48/60 (80%)
**Target for strong submission:** >= 54/60 (90%)
