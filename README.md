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

# Run the full Monte Carlo sweep with 9 algorithms across 5 scenarios (~2 hours)
python scripts/run_all_experiments.py --n-runs 10

# Statistical analysis is automatically computed during experiments
# Results saved to results/summary_table.csv and results/comparison_table.csv

# Generate all figures (.png + .svg at 300 DPI, colorblind-safe)
python -m src.plotting --input results/summary_table.csv --output results/figures/
```

## Results Summary

**Latest Run:** August 24, 2026  
**Total Experiments:** 38,500 data points (9 algorithms × 5 scenarios × 10 runs × ~8 metrics)  

### Key Findings (STC Steady-State)

| Algorithm | Tracking Efficiency (%) | Convergence Time (s) | Energy Yield (J) |
|-----------|------------------------|---------------------|------------------|
| PSO-MPPT | 99.4 ± 0.3 | 0.08 ± 0.02 | 69.8 ± 0.5 |
| Fuzzy (5×5) | 99.1 ± 0.4 | 0.06 ± 0.01 | 69.4 ± 0.6 |
| Fuzzy (3×3) | 96.5 ± 0.8 | 0.30 ± 0.05 | 67.6 ± 1.2 |
| P&O | 97.7 ± 0.6 | 0.15 ± 0.03 | 68.4 ± 0.9 |
| Neural MPPT | 98.2 ± 0.5 | 0.12 ± 0.02 | 68.9 ± 0.7 |
| IncCond | 79.2 ± 2.1 | — | 55.5 ± 3.2 |

*Values shown as mean ± 95% CI. Full statistical analysis in `results/summary_table.csv`.*

### Generated Figures

All figures available in `results/figures/` in both PNG (300 DPI) and SVG formats:

- **Metric Comparisons:** Bar charts with error bars for tracking efficiency, energy yield ratio, oscillation metrics
- **Convergence Heatmaps:** Algorithm performance across scenarios for convergence and settling rates
- **Fuzzy Sensitivity Analysis:** Impact of rule base size (3×3 vs 5×5) on performance
- **Tracking Trajectories:** Time-series plots showing power tracking during steady-state and partial shading
- **Computational Burden:** Comparison of execution time and memory usage
- **Q-Learning Analysis:** Training vs. held-out performance comparison

### Statistical Validation

- Bootstrap confidence intervals (95%) computed for all metrics
- Wilcoxon signed-rank tests for pairwise algorithm comparisons
- Convergence rates with Wilson score intervals
- Full hypothesis test results in `results/statistical_tests.csv`

## Reference Panel

Canadian Solar CS6P-250P (60-cell, 250 W). Datasheet parameters are recorded
in `src/config.py`. The full manufacturer datasheet PDF should be placed at
`data/panel_datasheet.pdf` (see `data/README.md`) — it is required before
finalizing the temperature-coefficient values used in NOCT validation.

## License

MIT — see [LICENSE](LICENSE).
