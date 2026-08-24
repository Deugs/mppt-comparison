# Data

`panel_datasheet.pdf` — Canadian Solar CS6P-230/235/240/245/250P "ClearPower"
full manufacturer datasheet (EN-Rev 3.50, Canadian Solar Inc., 2012), sourced
from a distributor mirror (selasenergy.gr) and cross-checked against multiple
independent distributor mirrors returning identical specs. STC values in this
PDF's CS6P-250P column match `src/config.py`'s `PANEL_*_STC` constants exactly
(Voc=37.2V, Isc=8.87A, Vmp=30.1V, Imp=8.30A, Pmax=250W, 60 cells), confirming
this is the correct datasheet.

Temperature coefficients extracted into `src/config.py`
(`KI_ISC_PCT_PER_C`/`KV_VOC_PCT_PER_C`/`KP_PMAX_PCT_PER_C`):
- Isc: +0.065 %/°C
- Voc: -0.34 %/°C
- Pmax: -0.43 %/°C
- NOCT: 45±2°C (matches `config.NOCT_CELL_TEMPERATURE_C`)

**Open item found while sourcing this:** `src/pv_model.py`'s `TwoDiodeModel`
does not currently use these coefficients directly — its temperature
dependence comes entirely from the thermal-voltage term `Vt = kT/q` inside
the diode equations (see `thermal_voltage()`), not from explicit Isc/Voc/Pmax
scaling. Whether that implicit temperature response quantitatively matches
the real panel's datasheet-specified coefficients above hasn't been checked;
this is exactly what the still-open NOCT/low-irradiance curve validation
(CLAUDE.md Phase 1) would test. This datasheet has the NOCT electrical table
needed for that validation (Pmax=181W, Vmp=27.5V, Imp=6.60A, Voc=34.2V,
Isc=7.19A at 800 W/m^2, 20°C ambient, for the 250P variant).
