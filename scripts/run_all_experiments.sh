#!/bin/bash
# Run All Experiments - Master Script
# This script executes the complete experimental pipeline for MPPT algorithm comparison

set -e  # Exit on error

echo "=========================================="
echo "MPPT Algorithm Comparison"
echo "Complete Experimental Pipeline"
echo "=========================================="
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/results"
FIGURES_DIR="$RESULTS_DIR/figures"

# Create output directories
mkdir -p "$RESULTS_DIR"
mkdir -p "$FIGURES_DIR"

echo "Project root: $PROJECT_ROOT"
echo "Results directory: $RESULTS_DIR"
echo ""

# Step 1: Run baseline experiments
echo "[Step 1/5] Running baseline MPPT algorithms..."
python3 "$SCRIPT_DIR/run_baseline_experiments.py"
echo "✓ Baseline experiments complete"
echo ""

# Step 2: Run partial shading scenarios
echo "[Step 2/5] Running partial shading experiments..."
python3 "$SCRIPT_DIR/run_partial_shading.py"
echo "✓ Partial shading experiments complete"
echo ""

# Step 3: Run Monte Carlo analysis
echo "[Step 3/5] Running Monte Carlo simulations (100 runs)..."
python3 "$SCRIPT_DIR/monte_carlo_analysis.py" --n-runs 100
echo "✓ Monte Carlo analysis complete"
echo ""

# Step 4: Statistical analysis
echo "[Step 4/5] Performing statistical analysis..."
python3 "$SCRIPT_DIR/statistical_analysis.py"
echo "✓ Statistical analysis complete"
echo ""

# Step 5: Generate figures
echo "[Step 5/5] Generating publication-ready figures..."
python3 "$SCRIPT_DIR/generate_figures.py" --style publication
echo "✓ Figures generated"
echo ""

echo "=========================================="
echo "Pipeline Complete!"
echo "=========================================="
echo ""
echo "Results saved to: $RESULTS_DIR"
echo "Figures saved to: $FIGURES_DIR"
echo ""
echo "Next steps:"
echo "  - Review results in $RESULTS_DIR"
echo "  - Check figures in $FIGURES_DIR"
echo "  - Run 'make paper' to compile manuscript"
echo ""
