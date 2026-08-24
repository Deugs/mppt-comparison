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

# Run the full 5-algorithm Monte Carlo sweep (~89 minutes)
python -m src.scenarios --monte-carlo 50 --output results/

# Statistical analysis (ANOVA, paired t-tests, summary table with 95% CIs)
python -m src.analysis --input results/comparison_table.csv --output results/

# Generate all figures (.png + .svg)
python -m src.plotting --input results/comparison_table.csv --output results/figures/
```

## Reference Panel

Canadian Solar CS6P-250P (60-cell, 250 W). Datasheet parameters are recorded
in `src/config.py`. The full manufacturer datasheet PDF should be placed at
`data/panel_datasheet.pdf` (see `data/README.md`) — it is required before
finalizing the temperature-coefficient values used in NOCT validation.

## License

MIT — see [LICENSE](LICENSE).
