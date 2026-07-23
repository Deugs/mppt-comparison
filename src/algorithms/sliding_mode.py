"""Sliding Mode Control (SMC) -- model-based nonlinear control.

Sliding surface: s = dP/dV, which is zero exactly at the MPP (the classic
choice for SMC-MPPT, since it needs no explicit reference voltage). Reaching
law: the exponential reaching law (Gao & Hung, 1993)

    ds/dt = -k*sign(s) - q*s,   k, q > 0

combines a constant-rate term (drives s to zero in finite time, dominates
far from the surface) with a proportional term (vanishes at s=0, avoiding
the overshoot a pure constant-rate law would cause). The discontinuous
sign(s) is the classic source of chattering; it is replaced here by a
boundary-layer saturation sat(s/PHI, BOUNDARY) (Slotine & Li, 1991), which
is linear (and therefore continuous) for |s/PHI| <= BOUNDARY and saturates
to +-1 outside it.

Mapping the reaching law onto a discrete duty-cycle correction: since
increasing duty cycle decreases the panel's operating voltage (the boost
converter's R_in = R*(1-D)^2 is monotonically decreasing in D), and s > 0
means the operating point is left of the MPP (needs higher V, i.e. lower
D), the correction carries a leading minus sign:

    deltaD = -(K * sat(e, BOUNDARY) + Q * e),   e = clip(s / PHI, -1, 1)

Lyapunov stability argument (CLAUDE.md, mandatory for the methodology
section): take V(s) = 0.5*s^2 as the Lyapunov candidate (positive definite,
zero only at s=0). Along the continuous-time reaching law,

    dV/dt = s * ds/dt = s*(-k*sign(s) - q*s) = -k*|s| - q*s^2 <= 0,

with equality only at s=0. Since k, q > 0, V is strictly decreasing whenever
s != 0, so s -> 0 asymptotically: the sliding surface (and therefore the
MPP) is reached and maintained. Within the boundary layer, replacing sign(s)
with the saturation function trades this strict guarantee for practical,
chattering-free convergence to a small residual band around s=0 -- the
standard boundary-layer tradeoff (Slotine & Li, 1991).

Citations (CLAUDE.md, mandatory): Utkin, V. (1977). "Variable structure
systems with sliding mode control." IEEE Transactions on Automatic Control,
22(2), 212-222 (general theory). Gao, W., and Hung, J.C. (1993). "Variable
structure control of nonlinear systems: A new approach." IEEE Transactions
on Industrial Electronics, 40(1), 45-55 (exponential reaching law). Slotine,
J.J.E., and Li, W. (1991). Applied Nonlinear Control. Prentice Hall
(boundary-layer method). The specific PV-SMC paper whose exact
surface/reaching-law combination this matches still needs to be identified
during the Phase 4 literature review (see config.py's citation flag) --
CLAUDE.md is explicit that there is no single "classic" SMC-MPPT paper the
way Femia (2005) is for P&O, so this should be picked to match the design
already made here, not the other way around.

Duty-cycle-clamp escape (found and fixed via the paper's peer-review audit
-- see CLAUDE.md Phase 2 / paper Section VII-B): a converter can only
present R_in = R_load*(1-D)^2 <= R_load, so at low irradiance the true MPP
can require an R_in never reachable at any valid duty cycle, however close
to MPPT_DUTY_MIN. Once clamped there, dV~=0 between samples, which reads as
s=dP/dV~=0 -- indistinguishable from genuinely reaching the sliding
surface. Left alone, this traps the controller at the clamp forever, since
delta_d then computes to (approximately) zero and never perturbs again,
even once a later irradiance rise makes the true MPP reachable. Fixed by
overriding delta_d with a small probe step away from a limit already
reached (reusing the bootstrap nudge's magnitude, since this is the same
"no trustworthy signal yet, just perturb and see" situation as the very
first step) whenever duty is already sitting at MPPT_DUTY_MIN/MPPT_DUTY_MAX
and the computed correction would hold or push further into it.
"""

from .. import config
from .base import MPPTAlgorithm


def _saturate(x: float, boundary: float) -> float:
    """Boundary-layer saturation: linear within +-boundary, clipped to +-1 outside."""
    scaled = x / boundary
    return max(-1.0, min(1.0, scaled))


class SlidingModeControl(MPPTAlgorithm):
    def __init__(
        self,
        phi_scale: float = config.SMC_PHI_SCALE,
        k_gain: float = config.SMC_K,
        q_gain: float = config.SMC_Q,
        boundary: float = config.SMC_BOUNDARY,
        bootstrap_step: float = config.SMC_BOOTSTRAP,
        duty_min: float = config.MPPT_DUTY_MIN,
        duty_max: float = config.MPPT_DUTY_MAX,
    ):
        self.phi_scale = phi_scale
        self.k_gain = k_gain
        self.q_gain = q_gain
        self.boundary = boundary
        self.bootstrap_step = bootstrap_step
        self.duty_min = duty_min
        self.duty_max = duty_max
        self.reset()

    def reset(self) -> None:
        self._v_prev = None
        self._p_prev = None

    def step(self, v: float, i: float, duty_cycle: float) -> float:
        p = v * i

        if self._v_prev is None:
            self._v_prev, self._p_prev = v, p
            # No dV history yet -- bootstrap with a small nudge so the next
            # call has a nonzero dV to compute the sliding surface s=dP/dV from.
            return min(max(duty_cycle + self.bootstrap_step, self.duty_min), self.duty_max)

        dv = v - self._v_prev
        dp = p - self._p_prev
        s = dp / dv if abs(dv) > 1e-9 else 0.0

        e = max(-1.0, min(1.0, s / self.phi_scale))
        delta_d = -(self.k_gain * _saturate(e, self.boundary) + self.q_gain * e)

        if duty_cycle <= self.duty_min and delta_d <= 0:
            delta_d = self.bootstrap_step
        elif duty_cycle >= self.duty_max and delta_d >= 0:
            delta_d = -self.bootstrap_step

        self._v_prev, self._p_prev = v, p
        return min(max(duty_cycle + delta_d, self.duty_min), self.duty_max)
