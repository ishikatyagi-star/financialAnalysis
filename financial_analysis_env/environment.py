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

    risks_found = sum(
        1 for risk in expected["top_risks"]
        if any(any(k in issue for k in RISK_KEYWORDS[risk]) for issue in issues)
    )
    if risks_found == 0:
        return 0.0

    reward = 0.5 * (risks_found / 3)
    reward += 0.3 * (sum(1 for n in expected["key_numbers"] if n in analysis) / 3)
    reward += 0.2 * (sum(1 for r in expected["top_risks"] if r in rec) / 3)
    reward *= min(len(action.identified_issues) / 3, 1)
    reward += 0.05 * min(
        sum(1 for w in ["because", "due to", "driven by", "as a result"] if w in analysis), 2
    )
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
            "growth_pct": 20.8,   # (290-240)/240 * 100 = 20.83%
        },
        "grader": lambda action, expected: (
            (0.4 if "q2" in " ".join(i.lower() for i in action.identified_issues) else 0.0)
            + (0.3 if any(x in action.analysis.lower() for x in ["20.8", "20%", "21%"]) else 0.0)
            + (0.3 if len(action.recommendation) > 20 else 0.0)
        ),
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
                "Month 8":  310,   # ← anomaly
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
        "grader": lambda action, expected: (
            (0.4 if "month 8" in " ".join(i.lower() for i in action.identified_issues) else 0.0)
            + (0.3 if any(w in action.analysis.lower() for w in ["spike", "anomaly", "unusual"]) else 0.0)
            + (0.3 if any(w in action.recommendation.lower() for w in ["investigate", "audit", "review", "check"]) else 0.0)
        ),
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
                "H2": 1380,   # key number
            },
            "gross_margin_pct": {
                "Q1": 68,
                "Q2": 63,
                "Q3": 58,
                "Q4": 51,    # key number — declining margin
            },
            "customer_acquisition": {
                "new_customers_H1": 42,
                "new_customers_H2": 39,
                "sales_marketing_spend_H1": 198,   # key number
                "sales_marketing_spend_H2": 310,
                "cac_H1": round(198 / 42, 1),      # ~4.7k
                "cac_H2": round(310 / 39, 1),      # ~7.9k
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