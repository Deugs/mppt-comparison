"""Perturb & Observe with adaptive step size.

Direction logic is self-referential in duty cycle (compare this step's power
change against the *previous* duty-cycle perturbation), which keeps the
algorithm agnostic to the sign of dV/dD -- it never needs to assume which way
voltage moves when duty cycle increases.

Citation (CLAUDE.md, mandatory): Femia, N., Petrone, G., Spagnuolo, G., and
Vitelli, M. (2005). "Optimization of perturb and observe maximum power point
tracking method." IEEE Transactions on Power Electronics, 20(4), 963-973.
"""

from .. import config
from .base import MPPTAlgorithm


class PerturbObserve(MPPTAlgorithm):
    def __init__(
        self,
        step_large: float = config.PO_STEP_LARGE,
        step_small: float = config.PO_STEP_SMALL,
        dpdv_threshold: float = config.PO_DPDV_THRESHOLD,
        duty_min: float = config.MPPT_DUTY_MIN,
        duty_max: float = config.MPPT_DUTY_MAX,
    ):
        self.step_large = step_large
        self.step_small = step_small
        self.dpdv_threshold = dpdv_threshold
        self.duty_min = duty_min
        self.duty_max = duty_max
        self.reset()

    def reset(self) -> None:
        self._v_prev = None
        self._p_prev = None
        self._d_prev = None

    def step(self, v: float, i: float, duty_cycle: float) -> float:
        p = v * i

        if self._v_prev is None:
            # No history yet: perturb in an arbitrary initial direction.
            new_duty = duty_cycle + self.step_large
        else:
            dp = p - self._p_prev
            dv = v - self._v_prev
            dd = duty_cycle - self._d_prev

            if dd == 0:
                direction = 1
            elif dp > 0:
                direction = 1 if dd > 0 else -1
            else:
                direction = -1 if dd > 0 else 1

            dpdv = dp / dv if abs(dv) > 1e-9 else float("inf")
            step_size = (
                self.step_large if abs(dpdv) > self.dpdv_threshold else self.step_small
            )
            new_duty = duty_cycle + direction * step_size

        self._v_prev, self._p_prev, self._d_prev = v, p, duty_cycle
        return min(max(new_duty, self.duty_min), self.duty_max)
