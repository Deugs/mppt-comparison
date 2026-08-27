# MPPT Algorithm Comparison - Makefile

# ==============================================================================
# Reproducible Research Automation
# ==============================================================================
# Usage:
#   make all          - Run complete pipeline (tests, experiments, plots)
#   make test         - Run test suite
#   make run          - Execute all experiments
#   make plot         - Generate all figures
#   make paper        - Compile LaTeX paper
#   make clean        - Remove generated files
#   make docker-build - Build Docker container
#   make docker-run   - Run experiments in Docker
# ==============================================================================

PYTHON := python3
PIP := pip
PYTEST := pytest
COVERAGE := coverage
BLACK := black
FLAKE8 := flake8

# Directories
SRC_DIR := src
TESTS_DIR := tests
RESULTS_DIR := results
FIGURES_DIR := $(RESULTS_DIR)/figures
DATA_DIR := data

# Files
REQUIREMENTS := requirements.txt
MONTE_CARLO_RUNS := 50

.PHONY: all test test-cov lint format check-format run analyze plot paper paper-clean clean clean-data clean-figs clean-pycache docker-build docker-run docker-shell repro-check help

# ==============================================================================
# Default target: complete pipeline
# ==============================================================================
all: lint test run plot
	@echo "✓ Complete pipeline finished successfully"

# ==============================================================================
# Testing
# ==============================================================================
test:
	@echo "Running tests..."
	$(PYTEST) $(TESTS_DIR)/ -v --tb=short

test-cov:
	@echo "Running tests with coverage..."
	$(COVERAGE) run --source=$(SRC_DIR) -m pytest $(TESTS_DIR)/ -v
	$(COVERAGE) report --show-missing
	$(COVERAGE) html -d htmlcov
	@echo "Coverage report generated in htmlcov/"

# ==============================================================================
# Code Quality
# ==============================================================================
lint:
	@echo "Running linter..."
	$(FLAKE8) $(SRC_DIR)/ --count --select=E9,F63,F7,F82 --show-source --statistics
	$(FLAKE8) $(SRC_DIR)/ --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics

format:
	@echo "Formatting code..."
	$(BLACK) $(SRC_DIR)/ $(TESTS_DIR)/ --line-length 100

check-format:
	@echo "Checking code formatting..."
	$(BLACK) $(SRC_DIR)/ $(TESTS_DIR)/ --line-length 100 --check

# ==============================================================================
# Experiments
# ==============================================================================
run:
	@echo "Running full Monte Carlo sweep ($(MONTE_CARLO_RUNS) runs x 11 scenarios x 5 algorithms)..."
	$(PYTHON) -m src.scenarios --monte-carlo $(MONTE_CARLO_RUNS) --output $(RESULTS_DIR)/
	@echo "✓ Experiments completed"

analyze:
	@echo "Running statistical analysis (ANOVA, paired t-tests, summary tables)..."
	$(PYTHON) -m src.analysis --input $(RESULTS_DIR)/comparison_table.csv --output $(RESULTS_DIR)/

# ==============================================================================
# Visualization
# ==============================================================================
plot: analyze
	@echo "Generating publication-ready figures..."
	$(PYTHON) -m src.plotting --input $(RESULTS_DIR)/summary_table.csv --output $(FIGURES_DIR)/
	@echo "✓ Figures saved to $(FIGURES_DIR)/"

# ==============================================================================
# Paper Compilation
# ==============================================================================
paper:
	@echo "Compiling LaTeX paper..."
	cd paper && pdflatex -interaction=nonstopmode main.tex
	cd paper && bibtex main.aux || true
	cd paper && pdflatex -interaction=nonstopmode main.tex
	cd paper && pdflatex -interaction=nonstopmode main.tex
	@echo "✓ Paper compiled: paper/main.pdf"

paper-clean:
	@echo "Cleaning LaTeX auxiliary files..."
	cd paper && rm -f *.aux *.log *.out *.bbl *.blg *.toc *.lof *.lot

# ==============================================================================
# Docker
# ==============================================================================
docker-build:
	@echo "Building Docker image..."
	docker build -t mppt-comparison:latest -f docker/Dockerfile .

docker-run:
	@echo "Running experiments in Docker..."
	docker run --rm -v $(PWD)/results:/app/results mppt-comparison:latest make run

docker-shell:
	@echo "Starting Docker shell..."
	docker run -it --rm -v $(PWD):/app mppt-comparison:latest bash

# ==============================================================================
# Data Management
# ==============================================================================
clean-data:
	@echo "Cleaning generated data..."
	rm -rf $(RESULTS_DIR)/*.csv
	rm -rf $(RESULTS_DIR)/*.pkl
	rm -rf $(RESULTS_DIR)/*.json

clean-figs:
	@echo "Cleaning figures..."
	rm -rf $(FIGURES_DIR)/*
	rm -rf htmlcov/

clean-pycache:
	@echo "Cleaning Python cache..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

clean: clean-data clean-figs clean-pycache paper-clean
	@echo "✓ Cleanup complete"

# ==============================================================================
# Reproducibility Check
# ==============================================================================
repro-check:
	@echo "Checking reproducibility requirements..."
	@test -f CITATION.cff || (echo "ERROR: CITATION.cff missing" && exit 1)
	@test -f LICENSE || (echo "ERROR: LICENSE missing" && exit 1)
	@test -f README.md || (echo "ERROR: README.md missing" && exit 1)
	@test -f $(REQUIREMENTS) || (echo "ERROR: requirements.txt missing" && exit 1)
	@echo "✓ All reproducibility artifacts present"

# ==============================================================================
# Help
# ==============================================================================
help:
	@echo "MPPT Algorithm Comparison - Available Targets:"
	@echo ""
	@echo "  Pipeline:"
	@echo "    make all          Run complete pipeline (lint, test, run, plot)"
	@echo ""
	@echo "  Testing:"
	@echo "    make test         Run test suite"
	@echo "    make test-cov     Run tests with coverage report"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make lint         Run linter"
	@echo "    make format       Format code with Black"
	@echo "    make check-format Check formatting without changes"
	@echo ""
	@echo "  Experiments:"
	@echo "    make run          Run full Monte Carlo sweep (50 runs x 11 scenarios x 5 algorithms)"
	@echo "    make analyze      Compute summary/ANOVA/t-test tables from results/comparison_table.csv"
	@echo ""
	@echo "  Visualization:"
	@echo "    make plot         Generate publication figures"
	@echo ""
	@echo "  Paper:"
	@echo "    make paper        Compile LaTeX paper"
	@echo "    make paper-clean  Remove LaTeX auxiliary files"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-build Build Docker image"
	@echo "    make docker-run   Run in Docker container"
	@echo "    make docker-shell Open shell in Docker"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make clean        Remove all generated files"
	@echo "    make clean-data   Remove experimental data"
	@echo "    make clean-figs   Remove figures"
	@echo "    make clean-pycache Remove Python cache"
	@echo ""
	@echo "  Other:"
	@echo "    make repro-check  Verify reproducibility artifacts"
	@echo "    make help         Show this help message"
