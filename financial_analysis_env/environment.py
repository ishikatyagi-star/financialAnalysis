import random
import os
from uuid import uuid4
from typing import Optional, Any, List

try:
    from .models import FinancialAnalysisAction, FinancialAnalysisObservation
except ImportError:
    from models import FinancialAnalysisAction, FinancialAnalysisObservation


# ── SMART KEYWORD SYSTEM ─────────────────────────────────────────────────────

RISK_KEYWORDS = {
    "margin": ["margin", "profitability", "gross margin", "margin decline"],
    "cac": ["cac", "customer acquisition cost", "acquisition cost"],
    "opex": ["opex", "operating expense", "cost increase", "expenses rising"]
}


def _hard_grader(action, expected):
    issues = [i.lower() for i in action.identified_issues]
    analysis = action.analysis.lower()
    rec = action.recommendation.lower()

    # Score how many of the 3 required risks appear in identified_issues
    risks_found = sum(
        1 for risk in expected["top_risks"]
        if any(any(k in issue for k in RISK_KEYWORDS[risk]) for issue in issues)
    )
    if risks_found == 0:
        return 0.0

    # Base: 0–0.5 based on risks found (0.5 only if all 3 found)
    reward = 0.5 * (risks_found / 3)

    # Up to 0.3 for citing key numbers in analysis
    numbers_cited = sum(1 for n in expected["key_numbers"] if n in analysis)
    reward += 0.3 * (numbers_cited / len(expected["key_numbers"]))

    # Up to 0.2 for addressing risks in recommendation
    risks_in_rec = sum(
        1 for risk in expected["top_risks"]
        if any(k in rec for k in RISK_KEYWORDS[risk])
    )
    reward += 0.2 * (risks_in_rec / 3)

    # Small causal language bonus, capped at +0.05
    causal_words = ["because", "due to", "driven by", "as a result"]
    causal_count = sum(1 for w in causal_words if w in analysis)
    reward += 0.05 * min(causal_count, 1)

    # Penalty if fewer than 3 issues identified
    if len(action.identified_issues) < 3:
        reward *= len(action.identified_issues) / 3

    return round(max(0.0, min(reward, 1.0)), 2)


def _easy_grader(action, expected):
    issues_text = " ".join(i.lower() for i in action.identified_issues)
    analysis = action.analysis.lower()
    rec = action.recommendation.lower()

    reward = 0.0

    # 0.4 for identifying Q2 as best quarter
    if "q2" in issues_text or "q2" in analysis:
        reward += 0.4

    # 0.3 for citing the growth percentage (must be specific)
    if any(x in analysis for x in ["20.8", "20.83"]):
        reward += 0.3
    elif any(x in analysis for x in ["20%", "21%"]):
        reward += 0.15  # partial credit for ballpark

    # 0.3 for a substantive recommendation
    action_words = ["invest", "replicate", "sustain", "promote", "campaign", "continue", "expand"]
    if len(rec) > 40 and any(w in rec for w in action_words):
        reward += 0.3
    elif len(rec) > 20:
        reward += 0.1  # partial credit

    return round(max(0.0, min(reward, 1.0)), 2)


def _medium_grader(action, expected):
    issues_text = " ".join(i.lower() for i in action.identified_issues)
    analysis = action.analysis.lower()
    rec = action.recommendation.lower()

    reward = 0.0

    # 0.4 for identifying month 8 specifically
    if "month 8" in issues_text or "month 8" in analysis:
        reward += 0.4

    # 0.3 for characterising the anomaly correctly
    anomaly_words = ["spike", "anomaly", "unusual", "outlier", "jump", "surge"]
    if any(w in analysis for w in anomaly_words):
        reward += 0.3

    # 0.3 for an actionable recommendation
    action_words = ["investigate", "audit", "review", "check", "examine", "escalate"]
    if any(w in rec for w in action_words):
        reward += 0.3

    # Penalty if issues list is empty
    if len(action.identified_issues) == 0:
        reward *= 0.5

    return round(max(0.0, min(reward, 1.0)), 2)


# ── TASK DEFINITIONS ──────────────────────────────────────────────────────────

TASKS = [
    # ── EASY ─────────────────────────────────────────────────────────────────
    {
        "difficulty": "easy",
        "task_description": (
            "You are a financial analyst. Below is quarterly revenue data for a retail company "
            "over the past year. Identify the best-performing quarter, calculate the growth "
            "percentage from Q1 to Q2, and provide a brief recommendation on how to sustain "
            "or build on that performance."
        ),
        "financial_data": {
            "company": "RetailCo",
            "period": "Annual",
            "currency": "USD (thousands)",
            "quarterly_revenue": {
                "Q1": 240,
                "Q2": 290,
                "Q3": 275,
                "Q4": 260,
            },
            "notes": "Q2 included a successful summer promotion campaign.",
        },
        "expected": {
            "best_quarter": "Q2",
            "growth_pct": 20.8,
        },
        "grader": lambda action, expected: _easy_grader(action, expected),
    },

    # ── MEDIUM ────────────────────────────────────────────────────────────────
    {
        "difficulty": "medium",
        "task_description": (
            "You are a financial analyst reviewing monthly expense data for a SaaS company. "
            "One month shows a significant anomaly in operating expenses. Identify which month "
            "contains the anomaly, explain what makes it unusual, and recommend an appropriate "
            "next step for the finance team."
        ),
        "financial_data": {
            "company": "SaaSify Inc.",
            "period": "January – December",
            "currency": "USD (thousands)",
            "monthly_opex": {
                "Month 1":  120,
                "Month 2":  118,
                "Month 3":  125,
                "Month 4":  122,
                "Month 5":  119,
                "Month 6":  123,
                "Month 7":  121,
                "Month 8":  310,
                "Month 9":  124,
                "Month 10": 120,
                "Month 11": 126,
                "Month 12": 122,
            },
            "notes": "No major planned events or one-time charges were pre-disclosed for Month 8.",
        },
        "expected": {
            "anomaly_month": "Month 8",
        },
        "grader": lambda action, expected: _medium_grader(action, expected),
    },

    # ── HARD ──────────────────────────────────────────────────────────────────
    {
        "difficulty": "hard",
        "task_description": (
            "You are a senior financial analyst conducting a comprehensive risk review for a "
            "B2B SaaS startup preparing for a Series B raise. Using the financial data below, "
            "identify the top three financial risks, support each risk with specific numbers "
            "from the data, and provide targeted recommendations. Consider margin trends, "
            "customer acquisition costs, and operating expense growth carefully."
        ),
        "financial_data": {
            "company": "GrowthLoop B2B",
            "period": "Last 12 months",
            "currency": "USD (thousands)",
            "revenue": {
                "H1": 1200,
                "H2": 1380,
            },
            "gross_margin_pct": {
                "Q1": 68,
                "Q2": 63,
                "Q3": 58,
                "Q4": 51,
            },
            "customer_acquisition": {
                "new_customers_H1": 42,
                "new_customers_H2": 39,
                "sales_marketing_spend_H1": 198,
                "sales_marketing_spend_H2": 310,
                "cac_H1": round(198 / 42, 1),
                "cac_H2": round(310 / 39, 1),
            },
            "operating_expenses": {
                "H1_total": 820,
                "H2_total": 1050,
                "yoy_opex_growth_pct": 28,
            },
            "notes": (
                "Company is pre-profitability. Headcount grew 35% in H2. "
                "No significant one-time charges recorded."
            ),
        },
        "expected": {
            "top_risks": ["margin", "cac", "opex"],
            "key_numbers": ["51", "198", "1380"],
        },
        "grader": lambda action, expected: _hard_grader(action, expected),
    },
]


# ── GLOBAL STATE ──────────────────────────────────────────────────────────────

_current_task = None
_current_state = {"episode_id": str(uuid4()), "step_count": 0}


# ── ENVIRONMENT CLASS ─────────────────────────────────────────────────────────

class FinancialAnalysisEnvironment:
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    async def reset_async(self, seed=None, options=None):
        return self.reset(seed=seed, options=options)

    async def step_async(self, action):
        return self.step(action)

    def seed(self, seed=None):
        random.seed(seed)

    metadata = {"render_modes": []}

    def reset(self, seed=None, options=None) -> FinancialAnalysisObservation:
        global _current_task, _current_state
        if seed is not None:
            random.seed(seed)

        _current_state = {
            "episode_id": options.get("episode_id", str(uuid4())) if options else str(uuid4()),
            "step_count": 0,
        }
        _current_task = random.choice(TASKS)

        return FinancialAnalysisObservation(
            task_description=_current_task["task_description"],
            financial_data=_current_task["financial_data"],
            difficulty=_current_task["difficulty"],
            done=False,
            reward=0.0,
        )

    def step(self, action: FinancialAnalysisAction) -> FinancialAnalysisObservation:
        global _current_task, _current_state
        _current_state["step_count"] += 1

        if _current_task is None:
            _current_task = random.choice(TASKS)

        reward = self._calculate_reward(action)

        return FinancialAnalysisObservation(
            task_description=_current_task["task_description"],
            financial_data=_current_task["financial_data"],
            difficulty=_current_task["difficulty"],
            done=True,
            reward=reward,
        )

    def _calculate_reward(self, action: FinancialAnalysisAction) -> float:
        task = _current_task
        grader = task.get("grader")
        if grader:
            return grader(action, task["expected"])
        return 0.0

    def close(self):
        pass

    @property
    def state(self) -> dict:
        return _current_state