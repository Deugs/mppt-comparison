"""Statistical analysis module for MPPT algorithm comparison.

This module provides statistical tools for rigorous analysis of MPPT algorithms,
including bootstrapping, hypothesis testing, and sensitivity analysis.
"""

from .bootstrap import BootstrapCI, bootstrap_confidence_interval
from .hypothesis_tests import (
    wilcoxon_signed_rank,
    anova_oneway,
    tukey_hsd,
    StatisticalComparison,
)
from .sensitivity import NoiseInjector, SensitivityAnalyzer, RobustnessEvaluator

__all__ = [
    "BootstrapCI",
    "bootstrap_confidence_interval",
    "wilcoxon_signed_rank",
    "anova_oneway",
    "tukey_hsd",
    "StatisticalComparison",
    "NoiseInjector",
    "SensitivityAnalyzer",
    "RobustnessEvaluator",
]
