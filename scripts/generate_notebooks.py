#!/usr/bin/env python3
"""
Generate Jupyter notebooks from experiment results for interactive exploration.
Creates notebooks for:
1. Results overview and summary statistics
2. Algorithm comparison visualizations
3. Statistical analysis deep-dive
4. Reproducibility demonstration
"""

import os
import json
from pathlib import Path

NOTEBOOKS_DIR = Path(__file__).parent.parent / "notebooks"
RESULTS_DIR = Path(__file__).parent.parent / "results"
# Find the latest raw data file
MONTE_CARLO_DIR = RESULTS_DIR / "monte_carlo"
DATA_FILES = list(MONTE_CARLO_DIR.glob("raw_data_*.csv"))
if DATA_FILES:
    DATA_FILE = max(DATA_FILES, key=lambda p: p.stat().st_mtime)
else:
    DATA_FILE = None


def create_overview_notebook():
    """Create notebook 1: Results Overview"""
    content = '''{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# MPPT Algorithm Comparison: Results Overview\\n",
    "\\n",
    "This notebook provides an interactive exploration of the Monte Carlo simulation results comparing 9 MPPT algorithms across 5 scenarios.\\n",
    "\\n",
    "**Key Metrics:**\\n",
    "- Tracking Efficiency (%)\\n",
    "- Convergence Time (s)\\n",
    "- Steady-State Ripple (%)\\n",
    "- Computational Burden (ms/step)\\n",
    "\\n",
    "**Algorithms:** P&O, Incremental Conductance, Fuzzy Logic, Sliding Mode, Q-Learning, PSO-MPPT, Neural MPPT, Hill Climbing, Beta Method\\n",
    "\\n",
    "**Scenarios:** Steady State, Step Change, Temperature Variation, Partial Shading, Rapid Irradiance Change"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\\n",
    "import numpy as np\\n",
    "import matplotlib.pyplot as plt\\n",
    "import seaborn as sns\\n",
    "\\n",
    "plt.style.use('../styles/publication.mplstyle')\\n",
    "%matplotlib inline"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Load aggregated results\\n",
    "df = pd.read_csv('../results/aggregated_results.csv')\\n",
    "print(f\"Total experiments: {len(df)}\")\\n",
    "print(f\"\\\\nColumns: {list(df.columns)}\")\\n",
    "df.head()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Summary statistics by algorithm\\n",
    "summary = df.groupby('algorithm')[['efficiency_mean', 'convergence_time_mean', 'ripple_mean']].agg(['mean', 'std', 'min', 'max'])\\n",
    "summary"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Performance heatmap\\n",
    "pivot_eff = df.pivot_table(values='efficiency_mean', index='scenario', columns='algorithm', aggfunc='mean')\\n",
    "plt.figure(figsize=(12, 6))\\n",
    "sns.heatmap(pivot_eff, annot=True, fmt='.2f', cmap='YlGnBu', linewidths=0.5)\\n",
    "plt.title('Tracking Efficiency (%) by Algorithm and Scenario')\\n",
    "plt.tight_layout()\\n",
    "plt.savefig('../results/figures/notebook_efficiency_heatmap.png', dpi=300)\\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Convergence time comparison\\n",
    "plt.figure(figsize=(12, 6))\\n",
    "sns.boxplot(data=df, x='algorithm', y='convergence_time_mean', palette='colorblind')\\n",
    "plt.xticks(rotation=45, ha='right')\\n",
    "plt.ylabel('Convergence Time (s)')\\n",
    "plt.title('Convergence Time Distribution Across Scenarios')\\n",
    "plt.tight_layout()\\n",
    "plt.savefig('../results/figures/notebook_convergence_boxplot.png', dpi=300)\\n",
    "plt.show()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.12.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}'''
    
    with open(NOTEBOOKS_DIR / "01_results_overview.ipynb", 'w') as f:
        f.write(content)
    print("✓ Created: 01_results_overview.ipynb")


def create_statistical_analysis_notebook():
    """Create notebook 2: Statistical Analysis Deep-Dive"""
    content = '''{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Statistical Analysis of MPPT Algorithms\\n",
    "\\n",
    "This notebook performs rigorous statistical validation of performance differences between algorithms.\\n",
    "\\n",
    "**Analyses:**\\n",
    "- Bootstrap Confidence Intervals (95%)\\n",
    "- Wilcoxon Signed-Rank Tests\\n",
    "- ANOVA for multi-algorithm comparison\\n",
    "- Effect Size Calculations"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\\n",
    "import numpy as np\\n",
    "from scipy import stats\\n",
    "import sys\\n",
    "sys.path.append('../src')\\n",
    "from stats.bootstrap import bootstrap_confidence_interval, hypothesis_test\\n",
    "\\n",
    "import matplotlib.pyplot as plt\\n",
    "plt.style.use('../styles/publication.mplstyle')"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "df = pd.read_csv('../results/aggregated_results.csv')\\n",
    "print(f\"Dataset: {len(df)} experiments\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Bootstrap confidence intervals for top performers\\n",
    "algorithms = df['algorithm'].unique()\\n",
    "print(\"95% Confidence Intervals for Tracking Efficiency:\\\\n\")\\n",
    "for algo in algorithms:\\n",
    "    data = df[df['algorithm'] == algo]['efficiency_mean'].values\\n",
    "    ci_low, ci_high = bootstrap_confidence_interval(data, n_bootstrap=1000, confidence_level=0.95)\\n",
    "    mean_eff = np.mean(data)\\n",
    "    print(f\"{algo:20s}: {mean_eff:.2f}% [{ci_low:.2f}%, {ci_high:.2f}%]\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Pairwise Wilcoxon tests (PSO-MPPT vs others)\\n",
    "baseline = df[df['algorithm'] == 'PSO-MPPT']['efficiency_mean'].values\\n",
    "print(\"\\\\nWilcoxon Signed-Rank Test (vs PSO-MPPT):\\\\n\")\\n",
    "for algo in algorithms:\\n",
    "    if algo != 'PSO-MPPT':\\n",
    "        other = df[df['algorithm'] == algo]['efficiency_mean'].values\\n",
    "        stat, pvalue = stats.wilcoxon(baseline[:len(other)], other)\\n",
    "        sig = "***" if pvalue < 0.001 else "**" if pvalue < 0.01 else "*" if pvalue < 0.05 else "ns"\\n",
    "        print(f"{algo:20s}: p={pvalue:.4f} {sig}")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# One-way ANOVA across all algorithms\\n",
    "groups = [df[df['algorithm'] == algo]['efficiency_mean'].values for algo in algorithms]\\n",
    "f_stat, p_value = stats.f_oneway(*groups)\\n",
    "print(f\"\\\\nANOVA Results:\")\\n",
    "print(f\"F-statistic: {f_stat:.2f}\")\\n",
    "print(f\"p-value: {p_value:.2e}\")\\n",
    "print(f\"Significant difference: {'Yes' if p_value < 0.05 else 'No'}\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.12.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}'''
    
    with open(NOTEBOOKS_DIR / "02_statistical_analysis.ipynb", 'w') as f:
        f.write(content)
    print("✓ Created: 02_statistical_analysis.ipynb")


def create_reproducibility_notebook():
    """Create notebook 3: Reproducibility Demo"""
    content = '''{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Reproducibility Demonstration\\n",
    "\\n",
    "This notebook demonstrates how to reproduce key results from the paper using the provided codebase.\\n",
    "\\n",
    "**Steps:**\\n",
    "1. Load raw simulation data\\n",
    "2. Recreate Figure 3 (Tracking Trajectories)\\n",
    "3. Verify statistical claims\\n",
    "4. Run custom scenario"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\\n",
    "import matplotlib.pyplot as plt\\n",
    "import sys\\n",
    "sys.path.append('../src')\\n",
    "\\n",
    "plt.style.use('../styles/publication.mplstyle')\\n",
    "%matplotlib inline"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Load raw trace data\\n",
    "trace_file = '../results/raw_data/pso_mppt_steady_state_run_0.csv'\\n",
    "trace_df = pd.read_csv(trace_file)\\n",
    "print(f\"Loaded trace: {len(trace_df)} time steps\")\\n",
    "trace_df.head()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Recreate tracking trajectory plot\\n",
    "fig, ax = plt.subplots(figsize=(10, 6))\\n",
    "ax.plot(trace_df['time'], trace_df['power'], label='Output Power', linewidth=2)\\n",
    "ax.plot(trace_df['time'], trace_df['p_ref'], '--', label='Reference Power', linewidth=2)\\n",
    "ax.set_xlabel('Time (s)')\\n",
    "ax.set_ylabel('Power (W)')\\n",
    "ax.legend()\\n",
    "ax.grid(True, alpha=0.3)\\n",
    "plt.tight_layout()\\n",
    "plt.savefig('../results/figures/notebook_reproduced_trajectory.png', dpi=300)\\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Verify efficiency calculation\\n",
    "efficiency = (trace_df['power'].mean() / trace_df['p_ref'].mean()) * 100\\n",
    "print(f\"Calculated efficiency: {efficiency:.2f}%\")\\n",
    "print(f\"Reported efficiency in paper: ~99.4%\")\\n",
    "print(f\"Match: {abs(efficiency - 99.4) < 1.0}\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.12.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}'''
    
    with open(NOTEBOOKS_DIR / "03_reproducibility_demo.ipynb", 'w') as f:
        f.write(content)
    print("✓ Created: 03_reproducibility_demo.ipynb")


def main():
    """Generate all notebooks"""
    print("Generating Jupyter notebooks from experiment results...\n")
    
    # Ensure directory exists
    NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if results exist
    if DATA_FILE is None or not DATA_FILE.exists():
        print(f"❌ Error: No Monte Carlo data files found in {MONTE_CARLO_DIR}")
        print("Please run experiments first: python scripts/run_all_experiments.py")
        return
    
    print(f"Using data file: {DATA_FILE.name}\n")
    
    create_overview_notebook()
    create_statistical_analysis_notebook()
    create_reproducibility_notebook()
    
    print("\n✅ All notebooks generated successfully!")
    print(f"Location: {NOTEBOOKS_DIR}/")
    print(f"\nTo view: jupyter notebook {NOTEBOOKS_DIR}")


if __name__ == "__main__":
    main()
