# MPPT Algorithm Comparison

Reproducible, open-source comparison of Maximum Power Point Tracking (MPPT)
algorithms for solar PV systems across four control paradigms — perturbative
(P&O, IncCond), rule-based (Fuzzy Logic), learning-based (Q-learning), and
model-based nonlinear control (Sliding Mode Control) — under varying
irradiance, temperature, and partial-shading conditions.

See [`CLAUDE.md`](CLAUDE.md) for the full research/implementation plan and
[`publication_supplement.md`](publication_supplement.md) for the IEEE
submission checklist and templates.

**Status:** Phases 1-3 complete (PV/converter models, all 5 algorithms, full
50-run Monte Carlo sweep across 11 scenarios). Phase 4 (statistical analysis,
figures) complete; literature review and paper writing in progress. See the
Status/TODO section of `CLAUDE.md` for the current checklist.

## Reproduction

```bash
# Install pinned dependencies
pip install -r requirements.txt

# Run sanity tests with coverage
pytest tests/ -v --cov=src

# One-command full reproduction (experiments + analysis + figures)
make all

# Or run steps individually:

# Run the full Monte Carlo sweep: 5 algorithms x 11 scenarios x 50 runs (~90 min)
python -m src.scenarios --monte-carlo 50 --output results/
# -> results/comparison_table.csv (long-format raw data)

# Compute summary statistics, ANOVA, and paired t-tests
python -m src.analysis --input results/comparison_table.csv --output results/
# -> results/summary_table.csv, results/statistical_tests.csv, results/fuzzy_sensitivity_table.csv

# Generate all figures (.png + .svg at 300 DPI, colorblind-safe)
python -m src.plotting --input results/summary_table.csv --output results/figures/
```

## Results Summary

See `CLAUDE.md`'s Phase 4 notes for the full, verified set of headline
findings from the 50-run x 11-scenario x 5-algorithm sweep (partial-shading
global-search failure, the Q-learning train/held-out generalization gap, the
fuzzy 5x5-vs-7x7 rule-reduction result, and per-algorithm computational
burden). Per-metric numbers with confidence intervals live in
`results/summary_table.csv`; ANOVA/paired-t-test results live in
`results/statistical_tests.csv`. Only 5 algorithms are compared in this
paper — see `RESEARCH_PROGRAM.md` for why metaheuristic/ANN baselines are
out of scope here and reserved for later papers in the series.

### Generated Figures

Figures are written to `results/figures/` in both PNG (300 DPI) and SVG formats:

- **Metric Comparisons:** Bar charts with error bars for tracking efficiency, energy yield ratio, oscillation metrics
- **Convergence Heatmaps:** Algorithm performance across scenarios for convergence and settling rates
- **Fuzzy Sensitivity Analysis:** Impact of rule base size (3×3 vs 5×5 vs 7×7) on performance
- **Tracking Trajectories:** Time-series plots showing power tracking during steady-state and partial shading
- **Computational Burden:** Comparison of per-step execution time
- **Q-Learning Analysis:** Training vs. held-out performance comparison

### Statistical Validation

- One-way ANOVA and paired t-tests (paired by Monte Carlo run ID) across the 5 core algorithms — `src/analysis.py`
- Convergence/settling rates reported with Wilson-score 95% confidence intervals
- Full hypothesis test results in `results/statistical_tests.csv`

## Reference Panel

Canadian Solar CS6P-250P (60-cell, 250 W). Datasheet parameters are recorded
in `src/config.py`. The full manufacturer datasheet PDF should be placed at
`data/panel_datasheet.pdf` (see `data/README.md`) — it is required before
finalizing the temperature-coefficient values used in NOCT validation.

## License

MIT — see [LICENSE](LICENSE).
