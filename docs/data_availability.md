# Data Availability Statement

## Data and Code Availability

All data, code, and experimental configurations supporting the findings of this study are openly available in the **[Repository Name]** repository at **[GitHub Repository URL]**.

### Repository Contents

The repository includes:

1. **Source Code**: Complete implementation of all 5 MPPT algorithms compared in this paper (P&O, Incremental Conductance, Fuzzy Logic, Q-Learning, Sliding Mode Control), the two-diode PV model, and DC-DC boost converter model. Metaheuristic (PSO) and ANN-based MPPT are explicitly out of scope for this paper -- see `RESEARCH_PROGRAM.md`.

2. **Experimental Data**:
   - Raw Monte Carlo simulation results: 5 algorithms x 11 scenarios x 50 runs per scenario-algorithm pair, long format (`results/comparison_table.csv`)
   - Aggregated performance metrics with 95% confidence intervals (`results/summary_table.csv`)
   - Statistical test results (one-way ANOVA, paired t-tests -- `results/statistical_tests.csv`)
   - Fuzzy rule-base sensitivity analysis (`results/fuzzy_sensitivity_table.csv`)

3. **Figures and Visualizations**:
   - All publication-quality figures in PNG and SVG formats
   - Plotting scripts for regeneration
   - Located in: `results/figures/`

4. **Reproducibility Tools**:
   - Dockerfile for containerized environment
   - Makefile with `run`/`analyze`/`plot` targets (`make all` for the full pipeline)
   - Located in: root directory and `scripts/`

5. **Documentation**:
   - README.md with setup and usage instructions
   - `CLAUDE.md` with the full research/implementation plan and status log
   - Cover letter template
   - LaTeX manuscript source files
   - Located in: `docs/`

### Access Instructions

#### Option 1: Direct Clone
```bash
git clone [GitHub Repository URL]
cd [repository-name]
make docker-build
make docker-run
```

#### Option 2: Zenodo Archive (upon acceptance)
A permanent archived version with DOI will be available at: **[Zenodo DOI Placeholder]**

### License

This work is licensed under the **MIT License** (code) and **CC-BY-4.0** (data and documentation), allowing unrestricted use, distribution, and reproduction with proper attribution.

### Contact

For questions regarding the data or code, please contact:
- **[Corresponding Author Name]**: [Email Address]
- **ORCID**: [ORCID ID]

### Version Information

- **Current Version**: v1.0.0-ieee-submission
- **Tag Date**: [Date]
- **Commit Hash**: [Git Commit SHA]

---

*This statement complies with the FAIR (Findable, Accessible, Interoperable, Reusable) data principles and the journal's open science policies.*
