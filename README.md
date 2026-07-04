# MPPT Algorithm Comparison

Reproducible, open-source comparison of Maximum Power Point Tracking (MPPT)
algorithms for solar PV systems across four control paradigms — perturbative
(P&O, IncCond), rule-based (Fuzzy Logic), learning-based (Q-learning), and
model-based nonlinear control (Sliding Mode Control) — under varying
irradiance, temperature, and partial-shading conditions.

See [`CLAUDE.md`](CLAUDE.md) for the full research/implementation plan and
[`publication_supplement.md`](publication_supplement.md) for the IEEE
submission checklist and templates.

**Status:** Phase 1 (Foundation) in progress — two-diode PV model and boost
converter implementation. See the Status/TODO section of `CLAUDE.md` for the
current checklist.

## Reproduction

```bash
# Install pinned dependencies
pip install -r requirements.txt

# Run sanity tests with coverage
pytest tests/ -v
```

## Reference Panel

Canadian Solar CS6P-250P (60-cell, 250 W). Datasheet parameters are recorded
in `src/config.py`. The full manufacturer datasheet PDF should be placed at
`data/panel_datasheet.pdf` (see `data/README.md`) — it is required before
finalizing the temperature-coefficient values used in NOCT validation.

## License

MIT — see [LICENSE](LICENSE).
