"""Unified MPPT algorithm interface.

Every algorithm (P&O, IncCond, Fuzzy, Q-learning, SMC) implements this so
scenarios.py can swap between them without special-casing (see CLAUDE.md
"Unified Interface").
"""

from abc import ABC, abstractmethod


class MPPTAlgorithm(ABC):
    @abstractmethod
    def step(self, v: float, i: float, duty_cycle: float) -> float:
        """Compute the new duty cycle given the current voltage, current, and duty cycle.

        Args:
            v: Measured PV voltage, V.
            i: Measured PV current, A.
            duty_cycle: Current converter duty cycle, in [0, 1].

        Returns:
            The updated duty cycle, in [0, 1].
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset all internal state for a new scenario/run."""
