"""Incremental Conductance with boundary-condition handling.

At the MPP, dP/dV = 0, which expands to I + V*(dI/dV) = 0, i.e.
dI/dV = -I/V. The sign of (dI/dV - (-I/V)) indicates which side of the MPP
the operating point is on; when dV is too small to trust that ratio (the
"dV ~ 0" boundary case), the sign of dI alone is used instead.

The algorithm reasons in terms of a desired voltage direction, then converts
that into a duty-cycle step via `-direction`, since a boost converter's
input voltage decreases as duty cycle increases (R_in = R*(1-D)^2 is
monotonically decreasing in D).

Citation (CLAUDE.md, mandatory): Hussein, K.H., Muta, I., Hoshino, T., and
Osakada, M. (1995). "Maximum photovoltaic power tracking: an algorithm for
rapidly changing atmospheric conditions." IEE Proceedings-Generation,
Transmission and Distribution, 142(1), 59-64.
"""

from .. import config
from .base import MPPTAlgorithm


class IncrementalConductance(MPPTAlgorithm):
    def __init__(
        self,
        step: float = config.INC_COND_STEP,
        dv_epsilon: float = config.INC_COND_DV_EPSILON,
        tolerance: float = config.INC_COND_TOLERANCE,
        duty_min: float = config.MPPT_DUTY_MIN,
        duty_max: float = config.MPPT_DUTY_MAX,
    ):
        self.step_size = step
        self.dv_epsilon = dv_epsilon
        self.tolerance = tolerance
        self.duty_min = duty_min
        self.duty_max = duty_max
        self.reset()

    def reset(self) -> None:
        self._v_prev = None
        self._i_prev = None

    def step(self, v: float, i: float, duty_cycle: float) -> float:
        if self._v_prev is None:
            direction = 1  # no history yet: perturb in an arbitrary initial direction
        else:
            dv = v - self._v_prev
            di = i - self._i_prev

            if abs(dv) < self.dv_epsilon:
                if abs(di) < self.tolerance:
                    direction = 0
                else:
                    direction = 1 if di > 0 else -1
            else:
                incremental_conductance = di / dv
                negative_avg_conductance = -i / v
                delta = incremental_conductance - negative_avg_conductance
                if abs(delta) < self.tolerance:
                    direction = 0
                elif delta > 0:
                    direction = 1
                else:
                    direction = -1

        self._v_prev, self._i_prev = v, i
        new_duty = duty_cycle - direction * self.step_size
        return min(max(new_duty, self.duty_min), self.duty_max)
