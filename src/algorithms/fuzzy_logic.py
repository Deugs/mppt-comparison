"""Fuzzy Logic Controller (Mamdani inference, centroid defuzzification).

Inputs: E = dP/dV (normalized to [-1, 1] by FUZZY_E_SCALE), and its
step-to-step change deltaE (normalized by FUZZY_CE_SCALE). Output: a duty
cycle step deltaD directly in [FUZZY_OUTPUT_MIN, FUZZY_OUTPUT_MAX].

Membership functions are triangular, evenly spaced, with shoulder (saturating)
sets at both ends of each universe -- the standard fuzzy-MPPT partition
(CLAUDE.md, "Membership Function Design").

Rule base: rather than hand-transcribing a 49-entry lookup table, the 7x7
rule base is *generated* from a simple, physically-motivated formula and then
verified (see tests/test_fuzzy_logic.py) to reproduce CLAUDE.md's literal
7x7 table exactly, entry for entry:

    D_level = clip(round_half_away_from_zero(-(E_level + CE_level) / 2))

where E/CE/D levels are integers counted from the center label (Z = 0) to
the extremes (NB/N = -half, PB/P = +half). This says: the further the
operating point is from the MPP and the faster it is moving away, the larger
and more oppositely-signed the corrective duty-cycle step should be -- which
is exactly the physical intent behind each of CLAUDE.md's per-rule
justifications (e.g. R1: E=NB, deltaE=NB -> deltaD=PB; R25: E=Z, deltaE=Z ->
deltaD=Z; R49: E=PB, deltaE=PB -> deltaD=NB). The same formula, applied to a
5-label or 3-label set, produces internally consistent (antisymmetric)
reduced rule bases for the sensitivity analysis CLAUDE.md calls for (5x5 and
3x3 rule-base reduction).

Input normalization gains (FUZZY_E_SCALE, FUZZY_CE_SCALE in config.py) were
grid-searched against the STC convergence sanity check -- see the citation
flag there for why the naive choice (E_SCALE matched to the dP/dV magnitude
right at V=0) sustained a limit-cycle oscillation instead of converging.

Citation (CLAUDE.md, mandatory): 7x7 membership-function/rule-base structure
has precedent in the fuzzy-MPPT literature; cite the specific paper whose
partition this most closely matches once the Phase 4 literature review
locks in a reference (see CLAUDE.md "Citation Flags").
"""

import math

from .. import config
from .base import MPPTAlgorithm

SEVEN_LABELS = ["NB", "NM", "NS", "Z", "PS", "PM", "PB"]
FIVE_LABELS = ["NB", "NS", "Z", "PS", "PB"]
THREE_LABELS = ["N", "Z", "P"]


def _round_half_away_from_zero(x: float) -> int:
    if x == 0:
        return 0
    return int(math.copysign(math.floor(abs(x) + 0.5), x))


def generate_rule_table(labels: list) -> dict:
    """Generate a symmetric E x CE -> D rule table for an odd-length label set.

    See module docstring for the generating formula and its physical
    rationale. `labels` must be ordered from most-negative to most-positive
    (e.g. ["NB", "NM", "NS", "Z", "PS", "PM", "PB"]).
    """
    n = len(labels)
    half = (n - 1) // 2

    def level(index: int) -> int:
        return index - half

    def label_for_level(lv: int) -> str:
        return labels[lv + half]

    table = {}
    for e_index, e_label in enumerate(labels):
        for ce_index, ce_label in enumerate(labels):
            raw = -(level(e_index) + level(ce_index)) / 2
            d_level = _round_half_away_from_zero(raw)
            d_level = max(-half, min(half, d_level))
            table[(e_label, ce_label)] = label_for_level(d_level)
    return table


def build_triangular_partition(labels: list, lo: float, hi: float):
    """Evenly spaced triangular membership functions with shoulder ends.

    Returns (centers, membership_fn), where membership_fn(x) -> {label: degree}.
    """
    n = len(labels)
    centers = [lo + k * (hi - lo) / (n - 1) for k in range(n)]

    def membership(x: float) -> dict:
        x = max(lo, min(hi, x))
        degrees = {}
        for k, label in enumerate(labels):
            if k == 0:
                if x <= centers[0]:
                    deg = 1.0
                elif x >= centers[1]:
                    deg = 0.0
                else:
                    deg = (centers[1] - x) / (centers[1] - centers[0])
            elif k == n - 1:
                if x >= centers[-1]:
                    deg = 1.0
                elif x <= centers[-2]:
                    deg = 0.0
                else:
                    deg = (x - centers[-2]) / (centers[-1] - centers[-2])
            else:
                left, center, right = centers[k - 1], centers[k], centers[k + 1]
                if x <= left or x >= right:
                    deg = 0.0
                elif x <= center:
                    deg = (x - left) / (center - left)
                else:
                    deg = (right - x) / (right - center)
            degrees[label] = deg
        return degrees

    return centers, membership


class FuzzyLogicController(MPPTAlgorithm):
    def __init__(
        self,
        labels: list = SEVEN_LABELS,
        e_scale: float = config.FUZZY_E_SCALE,
        ce_scale: float = config.FUZZY_CE_SCALE,
        output_domain: tuple = (config.FUZZY_OUTPUT_MIN, config.FUZZY_OUTPUT_MAX),
        defuzz_points: int = config.FUZZY_DEFUZZ_POINTS,
        duty_min: float = config.MPPT_DUTY_MIN,
        duty_max: float = config.MPPT_DUTY_MAX,
    ):
        self.labels = labels
        self.rule_table = generate_rule_table(labels)
        self.e_scale = e_scale
        self.ce_scale = ce_scale
        self.duty_min = duty_min
        self.duty_max = duty_max

        _, self._e_membership = build_triangular_partition(labels, -1.0, 1.0)
        _, self._ce_membership = build_triangular_partition(labels, -1.0, 1.0)
        _, output_membership = build_triangular_partition(labels, *output_domain)

        lo, hi = output_domain
        self._defuzz_grid = [
            lo + k * (hi - lo) / (defuzz_points - 1) for k in range(defuzz_points)
        ]
        self._output_mf_table = {
            label: [output_membership(x)[label] for x in self._defuzz_grid]
            for label in labels
        }

        self.reset()

    def reset(self) -> None:
        self._v_prev = None
        self._p_prev = None
        self._e_prev = 0.0

    def step(self, v: float, i: float, duty_cycle: float) -> float:
        p = v * i

        if self._v_prev is None:
            self._v_prev, self._p_prev = v, p
            # No dV history yet -- bootstrap with a small nudge so the next
            # call has a nonzero dV to compute dP/dV from (see
            # config.FUZZY_INITIAL_PERTURBATION).
            return min(
                max(duty_cycle + config.FUZZY_INITIAL_PERTURBATION, self.duty_min),
                self.duty_max,
            )

        dv = v - self._v_prev
        dp = p - self._p_prev
        dpdv = dp / dv if abs(dv) > 1e-9 else 0.0

        e = max(-1.0, min(1.0, dpdv / self.e_scale))
        ce = max(-1.0, min(1.0, (e - self._e_prev) / self.ce_scale))

        e_degrees = self._e_membership(e)
        ce_degrees = self._ce_membership(ce)

        output_activation = {label: 0.0 for label in self.labels}
        for e_label, e_deg in e_degrees.items():
            if e_deg == 0.0:
                continue
            for ce_label, ce_deg in ce_degrees.items():
                if ce_deg == 0.0:
                    continue
                firing = min(e_deg, ce_deg)
                d_label = self.rule_table[(e_label, ce_label)]
                if firing > output_activation[d_label]:
                    output_activation[d_label] = firing

        delta_d = self._centroid(output_activation)

        self._v_prev, self._p_prev, self._e_prev = v, p, e
        return min(max(duty_cycle + delta_d, self.duty_min), self.duty_max)

    def _centroid(self, output_activation: dict) -> float:
        numerator = 0.0
        denominator = 0.0
        for idx, x in enumerate(self._defuzz_grid):
            mu = 0.0
            for label, activation in output_activation.items():
                if activation == 0.0:
                    continue
                degree = self._output_mf_table[label][idx]
                if degree > 0.0:
                    mu = max(mu, min(degree, activation))
            numerator += mu * x
            denominator += mu
        return numerator / denominator if denominator > 0.0 else 0.0
