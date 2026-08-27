#!/usr/bin/env python3
"""
Generate Jupyter notebooks from experiment results for interactive exploration.
Creates notebooks for:
1. Results overview and summary statistics
2. Statistical analysis deep-dive (ANOVA / paired t-tests)
3. Reproducibility demonstration

Notebooks are built as plain Python dicts and written with json.dump() so
that cell source code (which routinely contains embedded double quotes,
e.g. f"...") is escaped correctly by the json module instead of by hand.
"""

import json
from pathlib import Path

NOTEBOOKS_DIR = Path(__file__).parent.parent / "notebooks"
RESULTS_DIR = Path(__file__).parent.parent / "results"

SUMMARY_FILE = RESULTS_DIR / "summary_table.csv"
COMPARISON_FILE = RESULTS_DIR / "comparison_table.csv"
STATS_FILE = RESULTS_DIR / "statistical_tests.csv"


def _lines(text):
    """Split multi-line text into an nbformat source list (each line, '\\n'-terminated except the last)."""
    parts = text.strip("\n").split("\n")
    return [p + "\n" for p in parts[:-1]] + [parts[-1]]


def _cell(cell_type, source_text):
    cell = {
        "cell_type": cell_type,
        "metadata": {},
        "source": _lines(source_text),
    }
    if cell_type == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
    return cell


NOTEBOOK_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11.0"},
}


def _write_notebook(filename, cells):
    notebook = {
        "cells": cells,
        "metadata": NOTEBOOK_METADATA,
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    path = NOTEBOOKS_DIR / filename
    with open(path, "w") as f:
        json.dump(notebook, f, indent=1)
        f.write("\n")
    print(f"✓ Created: {filename}")


def create_overview_notebook():
    """Create notebook 1: Results Overview"""
    cells = [
        _cell(
            "markdown",
            """
# MPPT Algorithm Comparison: Results Overview

Interactive exploration of the Monte Carlo simulation results comparing the
5 MPPT algorithms in this paper -- spanning perturbative (P&O, IncCond),
rule-based (Fuzzy Logic), learning-based (Q-learning), and model-based
(Sliding Mode Control) paradigms -- across 11 test scenarios (steady state,
irradiance/temperature transients, partial shading, sensor noise, and
rapid fluctuation).

**Key metrics:** tracking efficiency (%), convergence time (s), settling
time (s), steady-state oscillation, energy yield ratio, and per-step
execution time. See `CLAUDE.md` for full scenario and metric definitions.
""",
        ),
        _cell(
            "code",
            """
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('../styles/publication.mplstyle')
%matplotlib inline
""",
        ),
        _cell(
            "code",
            """
# Per (algorithm, scenario, metric) descriptive statistics, produced by:
#   python -m src.analysis --input results/comparison_table.csv --output results/
summary = pd.read_csv('../results/summary_table.csv')
print(f"Rows: {len(summary)}")
print(f"Algorithms: {sorted(summary['algorithm'].unique())}")
print(f"Scenarios: {sorted(summary['scenario'].unique())}")
summary.head()
""",
        ),
        _cell(
            "code",
            """
# Tracking efficiency heatmap: algorithm x scenario
eff = summary[summary['metric'] == 'tracking_efficiency_pct']
pivot_eff = eff.pivot_table(values='mean', index='scenario', columns='algorithm')

fig, ax = plt.subplots(figsize=(12, 6))
im = ax.imshow(pivot_eff.values, cmap='viridis', aspect='auto')
ax.set_xticks(range(len(pivot_eff.columns)))
ax.set_xticklabels(pivot_eff.columns, rotation=45, ha='right')
ax.set_yticks(range(len(pivot_eff.index)))
ax.set_yticklabels(pivot_eff.index)
for i in range(pivot_eff.shape[0]):
    for j in range(pivot_eff.shape[1]):
        val = pivot_eff.values[i, j]
        if not np.isnan(val):
            ax.text(j, i, f"{val:.1f}", ha='center', va='center', color='white', fontsize=8)
ax.set_title('Tracking Efficiency (%) by Algorithm and Scenario')
fig.colorbar(im, ax=ax, label='Tracking efficiency (%)')
plt.tight_layout()
plt.savefig('../results/figures/notebook_efficiency_heatmap.png', dpi=300)
plt.show()
""",
        ),
        _cell(
            "code",
            """
# Convergence time distribution per algorithm, from the raw Monte Carlo runs
raw = pd.read_csv('../results/comparison_table.csv')
conv = raw[raw['metric'] == 'convergence_time_s'].dropna(subset=['value'])

fig, ax = plt.subplots(figsize=(12, 6))
algorithms = sorted(conv['algorithm'].unique())
data = [conv[conv['algorithm'] == a]['value'].values for a in algorithms]
ax.boxplot(data, tick_labels=algorithms)
ax.set_xticklabels(algorithms, rotation=45, ha='right')
ax.set_ylabel('Convergence time (s)')
ax.set_title('Convergence Time Distribution Across Scenarios')
plt.tight_layout()
plt.savefig('../results/figures/notebook_convergence_boxplot.png', dpi=300)
plt.show()
""",
        ),
    ]
    _write_notebook("01_results_overview.ipynb", cells)


def create_statistical_analysis_notebook():
    """Create notebook 2: Statistical Analysis Deep-Dive"""
    cells = [
        _cell(
            "markdown",
            """
# Statistical Analysis of MPPT Algorithms

Loads the ANOVA and paired-t-test results produced by `src/analysis.py`
(`run_anova`, `run_pairwise_ttests`) over the 5 core algorithms, paired by
Monte Carlo run ID per the identical-seed design in `src/scenarios.py`.

**Analyses:**
- One-way ANOVA across all 5 algorithms, per (scenario, metric)
- Paired t-tests between each algorithm pair, per (scenario, metric)
- Convergence/settling rates with Wilson-score 95% confidence intervals
""",
        ),
        _cell(
            "code",
            """
import pandas as pd

summary = pd.read_csv('../results/summary_table.csv')
stats_df = pd.read_csv('../results/statistical_tests.csv')
print(f"Summary rows: {len(summary)}")
print(f"Statistical test rows: {len(stats_df)} ({(stats_df['test'] == 'anova').sum()} ANOVA, "
      f"{(stats_df['test'] == 'paired_ttest').sum()} paired t-test)")
""",
        ),
        _cell(
            "code",
            """
# Mean tracking efficiency with 95% CI at steady state, per algorithm
steady = summary[(summary['scenario'] == 'steady_state') & (summary['metric'] == 'tracking_efficiency_pct')]
steady[['algorithm', 'mean', 'ci95_low', 'ci95_high', 'n_valid']].sort_values('mean', ascending=False)
""",
        ),
        _cell(
            "code",
            """
# ANOVA across all 5 algorithms for tracking efficiency, one row per scenario
anova = stats_df[(stats_df['test'] == 'anova') & (stats_df['metric'] == 'tracking_efficiency_pct')]
anova
""",
        ),
        _cell(
            "code",
            """
# Paired t-tests for tracking efficiency at steady state
ttests = stats_df[
    (stats_df['test'] == 'paired_ttest')
    & (stats_df['scenario'] == 'steady_state')
    & (stats_df['metric'] == 'tracking_efficiency_pct')
]
ttests
""",
        ),
    ]
    _write_notebook("02_statistical_analysis.ipynb", cells)


def create_reproducibility_notebook():
    """Create notebook 3: Reproducibility Demo"""
    cells = [
        _cell(
            "markdown",
            """
# Reproducibility Demonstration

Demonstrates reproducing a tracking-trajectory result directly from the
codebase (no stored per-timestep trace files are shipped -- trajectories
are always regenerated live from `src/scenarios.py`, the same code path
used to produce the paper's trajectory figures).

**Steps:**
1. Build the validated PV model and the 5 MPPT algorithms
2. Re-simulate the steady-state (STC) scenario for P&O
3. Recreate a tracking-trajectory plot
4. Recompute tracking efficiency and compare against `results/summary_table.csv`
""",
        ),
        _cell(
            "code",
            """
import sys
sys.path.append('..')
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('../styles/publication.mplstyle')
%matplotlib inline
""",
        ),
        _cell(
            "code",
            """
from src import config
from src.pv_model import TwoDiodeModel, extract_two_diode_parameters
from src.scenarios import build_default_algorithms, scenario_steady_state, run_scenario

panel_params = extract_two_diode_parameters(
    voc=config.PANEL_VOC_STC, isc=config.PANEL_ISC_STC,
    vmp=config.PANEL_VMP_STC, imp=config.PANEL_IMP_STC,
)
pv_model = TwoDiodeModel(panel_params, num_cells=config.PANEL_NS)
algorithms = build_default_algorithms(pv_model)
result = run_scenario(scenario_steady_state(), algorithms['p_and_o'], pv_model)
print(f"Simulated {len(result.times)} time steps for P&O at STC")
""",
        ),
        _cell(
            "code",
            """
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(result.times, result.powers, label='Output Power', linewidth=2)
ax.plot(result.times, result.theoretical_max_powers, '--', label='Theoretical MPP', linewidth=2)
ax.set_xlabel('Time (s)')
ax.set_ylabel('Power (W)')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('../results/figures/notebook_reproduced_trajectory.png', dpi=300)
plt.show()
""",
        ),
        _cell(
            "code",
            """
efficiency = 100.0 * np.trapz(result.powers, result.times) / np.trapz(result.theoretical_max_powers, result.times)
print(f"Calculated tracking efficiency: {efficiency:.2f}%")
print("Compare against results/summary_table.csv (algorithm=p_and_o, scenario=steady_state, metric=tracking_efficiency_pct)")
""",
        ),
    ]
    _write_notebook("03_reproducibility_demo.ipynb", cells)


def main():
    """Generate all notebooks"""
    print("Generating Jupyter notebooks from experiment results...\n")

    NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)

    if not SUMMARY_FILE.exists() or not COMPARISON_FILE.exists():
        print(f"❌ Error: results not found ({SUMMARY_FILE}, {COMPARISON_FILE})")
        print("Please run the pipeline first:")
        print("  python -m src.scenarios --monte-carlo 50 --output results/")
        print("  python -m src.analysis --input results/comparison_table.csv --output results/")
        return

    create_overview_notebook()
    create_statistical_analysis_notebook()
    create_reproducibility_notebook()

    print("\n✅ All notebooks generated successfully!")
    print(f"Location: {NOTEBOOKS_DIR}/")
    print(f"\nTo view: jupyter notebook {NOTEBOOKS_DIR}")


if __name__ == "__main__":
    main()
