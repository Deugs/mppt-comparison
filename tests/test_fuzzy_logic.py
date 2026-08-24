import pytest

from src import config
from src.algorithms.fuzzy_logic import (FIVE_LABELS, SEVEN_LABELS,
                                        THREE_LABELS, FuzzyLogicController,
                                        build_triangular_partition,
                                        generate_rule_table)
from tests._helpers import run_tracking, true_mpp_power

# Literal transcription of CLAUDE.md's 7x7 rule base (E rows, deltaE columns,
# both ordered NB, NM, NS, Z, PS, PM, PB) -- the ground truth the generated
# table must reproduce exactly.
CLAUDE_MD_TABLE_ROWS = [
    ["PB", "PB", "PM", "PM", "PS", "PS", "Z"],
    ["PB", "PM", "PM", "PS", "PS", "Z", "NS"],
    ["PM", "PM", "PS", "PS", "Z", "NS", "NS"],
    ["PM", "PS", "PS", "Z", "NS", "NS", "NM"],
    ["PS", "PS", "Z", "NS", "NS", "NM", "NM"],
    ["PS", "Z", "NS", "NS", "NM", "NM", "NB"],
    ["Z", "NS", "NS", "NM", "NM", "NB", "NB"],
]


def test_generated_rule_table_matches_claude_md_table():
    generated = generate_rule_table(SEVEN_LABELS)
    for row_index, e_label in enumerate(SEVEN_LABELS):
        for col_index, ce_label in enumerate(SEVEN_LABELS):
            expected = CLAUDE_MD_TABLE_ROWS[row_index][col_index]
            assert generated[(e_label, ce_label)] == expected, (
                f"rule ({e_label}, {ce_label}) expected {expected}, "
                f"got {generated[(e_label, ce_label)]}"
            )


def test_rule_table_center_rule_is_no_change():
    generated = generate_rule_table(SEVEN_LABELS)
    assert generated[("Z", "Z")] == "Z"


@pytest.mark.parametrize("labels", [SEVEN_LABELS, FIVE_LABELS, THREE_LABELS])
def test_rule_table_is_antisymmetric(labels):
    """f(E, CE) must equal the negation of f(-E, -CE) for a physically consistent table."""
    table = generate_rule_table(labels)
    n = len(labels)
    for i, e_label in enumerate(labels):
        for j, ce_label in enumerate(labels):
            d_label = table[(e_label, ce_label)]
            opposite_d_label = table[(labels[n - 1 - i], labels[n - 1 - j])]
            d_index = labels.index(d_label)
            assert labels.index(opposite_d_label) == n - 1 - d_index


@pytest.mark.parametrize("labels", [SEVEN_LABELS, FIVE_LABELS, THREE_LABELS])
def test_membership_partition_sums_to_one(labels):
    _, membership = build_triangular_partition(labels, -1.0, 1.0)
    for x in [-1.0, -0.6, -0.2, 0.0, 0.2, 0.6, 1.0]:
        degrees = membership(x)
        assert sum(degrees.values()) == pytest.approx(1.0, abs=1e-9)
        assert all(0.0 <= d <= 1.0 for d in degrees.values())


@pytest.mark.parametrize("labels", [SEVEN_LABELS, FIVE_LABELS, THREE_LABELS])
def test_finds_mpp_at_stc(pv_model_stc, labels):
    algorithm = FuzzyLogicController(labels=labels)
    history = run_tracking(algorithm, pv_model_stc, iterations=800)

    mpp_power = true_mpp_power(pv_model_stc)
    steady_state_powers = [v * i for v, i, _ in history[-50:]]
    mean_power = sum(steady_state_powers) / len(steady_state_powers)

    relative_error = abs(mean_power - mpp_power) / mpp_power
    assert relative_error < config.MPPT_CONVERGENCE_THRESHOLD


def test_reset_clears_history():
    algorithm = FuzzyLogicController()
    algorithm.step(30.0, 8.0, 0.3)
    assert algorithm._v_prev is not None

    algorithm.reset()
    assert algorithm._v_prev is None
    assert algorithm._p_prev is None
    assert algorithm._e_prev == 0.0


def test_duty_cycle_stays_within_bounds(pv_model_stc):
    algorithm = FuzzyLogicController()
    history = run_tracking(algorithm, pv_model_stc, iterations=300)
    duty_cycles = [d for _, _, d in history]
    assert all(config.MPPT_DUTY_MIN <= d <= config.MPPT_DUTY_MAX for d in duty_cycles)
