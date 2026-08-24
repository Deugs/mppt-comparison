"""Baseline MPPT algorithms for state-of-the-art comparison.

This module implements modern MPPT algorithms including PSO, neural networks,
and reinforcement learning approaches for comprehensive benchmarking.
"""

from .pso_mppt import PSOMPPT
from .neural_mppt import NeuralMPPT, MLPTracker

# RL implementation is optional and requires additional dependencies
try:
    from .rl_mppt import RLMPPT, DQNTracker
    __all__ = [
        "PSOMPPT",
        "NeuralMPPT",
        "MLPTracker",
        "RLMPPT",
        "DQNTracker",
    ]
except ImportError:
    __all__ = [
        "PSOMPPT",
        "NeuralMPPT",
        "MLPTracker",
    ]
