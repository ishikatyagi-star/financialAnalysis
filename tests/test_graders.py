"""Boundary tests for all four public graders.

Every grader must return a float strictly inside (0, 1) for every possible
input, including None, empty dict, empty action, and maximally filled action.
These tests mirror what the OpenEnv validator checks before accepting a submission.
"""

import pytest
from financial_analysis_env import grade_easy, grade_medium, grade_hard, grade_expert
from financial_analysis_env.models import FinancialAnalysisAction

GRADERS = [grade_easy, grade_medium, grade_hard, grade_expert]
GRADER_IDS = ["grade_easy", "grade_medium", "grade_hard", "grade_expert"]

EDGE_CASES = [
    None,                           # validator may call with no arg
    {},                             # validator may call with empty dict
    FinancialAnalysisAction(),      # all fields at default (empty strings / empty list)
    FinancialAnalysisAction(        # maximally noisy junk
        analysis="x" * 2000,
        identified_issues=["i"] * 20,
        recommendation="r" * 2000,
    ),
]
EDGE_IDS = ["none", "empty_dict", "empty_action", "junk_action"]


@pytest.mark.parametrize("grader", GRADERS, ids=GRADER_IDS)
@pytest.mark.parametrize("action", EDGE_CASES, ids=EDGE_IDS)
def test_score_strictly_inside_open_interval(grader, action):
    score = grader(action)
    assert isinstance(score, float), (
        f"{grader.__name__} returned {type(score).__name__}, expected float"
    )
    assert score > 0.0, (
        f"{grader.__name__} returned {score} for input '{action}' — must be > 0.0"
    )
    assert score < 1.0, (
        f"{grader.__name__} returned {score} for input '{action}' — must be < 1.0"
    )


@pytest.mark.parametrize("grader", GRADERS, ids=GRADER_IDS)
def test_score_never_exactly_zero(grader):
    """The most dangerous boundary: near-zero inputs must not produce exactly 0.0."""
    assert grader(None) != 0.0
    assert grader(FinancialAnalysisAction()) != 0.0


@pytest.mark.parametrize("grader", GRADERS, ids=GRADER_IDS)
def test_score_never_exactly_one(grader):
    """Perfect-looking input must not produce exactly 1.0 due to _clamp ceiling."""
    perfect = FinancialAnalysisAction(
        analysis=(
            "Q2 is the best quarter with 20.8% growth. "
            "Month 8 shows a 310 anomaly spike. "
            "Gross margin 51%, CAC rose from 4.7 to 7.9, OPEX up 28%. "
            "Cash runway is 8 months, covenant breach risk due to debt obligations. "
            "H2 revenue 1380, H1 sales marketing spend 198. "
            "Driven by headcount growth, as a result of rising acquisition costs. "
            "Because of margin compression, attributed to OPEX surge."
        ),
        identified_issues=["margin decline", "cac increase", "opex growth", "covenant risk"],
        recommendation=(
            "Replicate Q2 promotions to sustain revenue growth. "
            "Investigate month 8 expense charge with audit team. "
            "Improve gross margin, reduce CAC efficiency, control OPEX headcount. "
            "Bridge financing or cut burn rate to extend runway and reduce covenant risk."
        ),
    )
    assert grader(perfect) != 1.0


@pytest.mark.parametrize("grader", GRADERS, ids=GRADER_IDS)
def test_score_is_reproducible(grader):
    """Same input must produce the same score on repeated calls."""
    action = FinancialAnalysisAction(
        analysis="Q2 revenue grew 20.8%. Month 8 anomaly at 310. Margin 51%.",
        identified_issues=["q2 best quarter", "month 8 spike"],
        recommendation="Investigate and sustain performance.",
    )
    scores = [grader(action) for _ in range(3)]
    assert len(set(scores)) == 1, f"{grader.__name__} is not deterministic: {scores}"


@pytest.mark.parametrize("grader", GRADERS, ids=GRADER_IDS)
def test_partial_credit_increases_score(grader):
    """A filled action should score higher than an empty action (partial credit works).

    The action includes keywords relevant to every grader so none triggers an
    early-exit zero path (e.g. grade_hard requires 'margin', 'cac', or 'opex'
    in identified_issues to avoid its n_risks==0 early return).
    """
    empty_score = grader(FinancialAnalysisAction())
    filled_score = grader(FinancialAnalysisAction(
        analysis=(
            "Q2 revenue grew 20.8%. Month 8 anomaly at 310. "
            "Gross margin declined to 51%. CAC rose from 4.7 to 7.9. "
            "OPEX grew 28%. Cash runway is 8 months, covenant risk identified."
        ),
        identified_issues=["margin decline", "cac increase", "opex growth"],
        recommendation="Investigate month 8 anomaly, reduce CAC, sustain Q2 growth.",
    ))
    assert filled_score > empty_score, (
        f"{grader.__name__}: filled action ({filled_score}) should beat empty ({empty_score})"
    )
