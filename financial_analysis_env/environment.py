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


# ── TASK DEFINITIONS ──────────────────────────────────────────────────────────

TASKS = [
    {
        "difficulty": "easy",
        "task_description": (
            "Below is quarterly revenue data for a company (in $M). "
            "Identify which quarter had the highest revenue GROWTH compared to the previous quarter. "
            "In your analysis, state the quarter name and calculate the growth percentage. "
            "In identified_issues, put the winning quarter name (e.g. 'Q2'). "
            "In recommendation, suggest one thing the company should do to sustain this growth."
        ),
        "financial_data": {
            "Q1": 120,
            "Q2": 145,
            "Q3": 152,
            "Q4": 158,
        },
        "expected": {
            "best_quarter": "Q2",
            "growth_pct": 20.8,
        },
    },
    {
        "difficulty": "medium",
        "task_description": (
            "Below is a monthly P&L summary (in $K) for a company. "
            "Revenue has been stable. Analyze the expense column and identify any anomaly. "
            "In your analysis, name the month with the anomaly and explain what it likely means. "
            "In identified_issues, list the anomalous month (e.g. 'Month 8'). "
            "In recommendation, suggest what the finance team should investigate."
        ),
        "financial_data": {
            "revenue": {f"Month {i}": 500 for i in range(1, 13)},
            "expenses": {
                "Month 1": 310, "Month 2": 318, "Month 3": 305,
                "Month 4": 312, "Month 5": 308, "Month 6": 315,
                "Month 7": 311, "Month 8": 487,
                "Month 9": 309, "Month 10": 314, "Month 11": 307, "Month 12": 313,
            },
        },
        "expected": {
            "anomaly_month": "Month 8",
        },
    },
    {
        "difficulty": "hard",
        "task_description": (
            "Below is 3 years of annual financial data for a company. "
            "Analyze trends across revenue, gross margin, operating expenses, and CAC. "
            "Identify top 3 risks with supporting numbers. "
            "List 3 risks in identified_issues and give actions in recommendation."
        ),
        "financial_data": {
            "Year 1": {"revenue": 2100, "gross_margin_pct": 62, "opex": 980, "CAC": 120},
            "Year 2": {"revenue": 2250, "gross_margin_pct": 57, "opex": 1150, "CAC": 155},
            "Year 3": {"revenue": 2280, "gross_margin_pct": 51, "opex": 1380, "CAC": 198},
        },
        "expected": {
            "top_risks": ["margin", "cac", "opex"],
            "key_numbers": ["51", "198", "1380"],
        },
    },
]


# ── GLOBAL STATE ──────────────────────────────────────────────────────────────

_current_task = None
_current_state = {"episode_id": str(uuid4()), "step_count": 0}


# ── ENVIRONMENT CLASS ─────────────────────────────────────────────────────────

class FinancialAnalysisEnvironment:
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    # --- ADD THESE FOUR LINES TO FIX THE NEW ERROR ---
    def reset_async(self): pass 
    def step_async(self): pass
    def seed(self, seed=None): pass
    metadata = {"render_modes": []}
    # ------------------------------------------------

    def reset(self, seed=None, options=None) -> FinancialAnalysisObservation:
        global _current_task, _current_state
        if seed is not None:
            random.seed(seed)

        _current_state = {
            "episode_id": options.get("episode_id", str(uuid4())) if options else str(uuid4()),
            "step_count": 0
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
        difficulty = task["difficulty"]
        expected = task["expected"]
        analysis = action.analysis.lower()
        issues = [i.lower() for i in action.identified_issues]
        rec = action.recommendation.lower()

        if len(analysis.strip()) < 20:
            return 0.0

        reward = 0.0
        if difficulty == "easy":
            if "q2" in " ".join(issues): reward += 0.4
            if any(x in analysis for x in ["20.8", "20%", "21%"]): reward += 0.3
            if len(action.recommendation) > 20: reward += 0.3
        elif difficulty == "medium":
            if "month 8" in " ".join(issues): reward += 0.4
            if any(word in analysis for word in ["spike", "anomaly", "unusual"]): reward += 0.3
            if any(word in rec for word in ["investigate", "audit", "review", "check"]): reward += 0.3
        elif difficulty == "hard":
            risks_found = sum(1 for risk in expected["top_risks"] if any(any(k in issue for k in RISK_KEYWORDS[risk]) for issue in issues))
            if risks_found == 0: return 0.0
            reward += 0.5 * (risks_found / 3)
            facts_hit = sum(1 for n in expected["key_numbers"] if n in analysis)
            reward += 0.3 * (facts_hit / 3)
            rec_hits = sum(1 for risk in expected["top_risks"] if risk in rec)
            reward += 0.2 * (rec_hits / 3)
            reward *= min(len(action.identified_issues) / 3, 1)

        return float(round(max(0.0, min(reward, 1.0)), 2))

    def close(self):
        pass

    @property
    def state(self) -> dict:
        return _current_state