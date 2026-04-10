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

# ── GRADER LOGIC ─────────────────────────────────────────────────────────────

def _hard_grader(action, expected):
    issues = [i.lower() for i in action.identified_issues]
    analysis = action.analysis.lower()
    rec = action.recommendation.lower()
    
    risks_found = sum(
        1 for risk in expected["top_risks"]
        if any(any(k in issue for k in RISK_KEYWORDS[risk]) for issue in issues)
    )
    
    # Start with a tiny baseline to stay above 0.0
    reward = 0.05
    
    if risks_found > 0:
        reward += 0.4 * (risks_found / 3)
        reward += 0.3 * (sum(1 for n in expected["key_numbers"] if n in analysis) / 3)
        reward += 0.2 * (sum(1 for r in expected["top_risks"] if r in rec) / 3)
    
    # Clamp strictly between 0 and 1
    return float(round(max(0.01, min(reward, 0.99)), 2))

# ── TASK DEFINITIONS ──────────────────────────────────────────────────────────

TASKS = [
    {
        "difficulty": "easy",
        "task_description": (
            "Below is quarterly revenue data for a company (in $M). "
            "Identify which quarter had the highest revenue GROWTH compared to the previous quarter. "
            "In identified_issues, put the winning quarter name (e.g. 'Q2')."
        ),
        "financial_data": {"Q1": 120, "Q2": 145, "Q3": 152, "Q4": 158},
        "expected": {"best_quarter": "Q2", "growth_pct": 20.8},
        "grader": lambda action, expected: float(round(max(0.01, min(
            (0.35 if "q2" in " ".join(i.lower() for i in action.identified_issues) else 0.0) +
            (0.3 if any(x in action.analysis.lower() for x in ["20.8", "20%", "21%"]) else 0.0) +
            (0.3 if len(action.recommendation) > 20 else 0.05)
        , 0.99)), 2)),
    },
    {
        "difficulty": "medium",
        "task_description": (
            "Below is a monthly P&L summary. Analyze expenses and identify the anomaly. "
            "In identified_issues, list the anomalous month (e.g. 'Month 8')."
        ),
        "financial_data": {
            "expenses": {"Month 1": 310, "Month 7": 311, "Month 8": 487, "Month 9": 309}
        },
        "expected": {"anomaly_month": "Month 8"},
        "grader": lambda action, expected: float(round(max(0.01, min(
            (0.35 if "month 8" in " ".join(i.lower() for i in action.identified_issues) else 0.0) +
            (0.3 if any(w in action.analysis.lower() for w in ["spike", "anomaly"]) else 0.0) +
            (0.3 if len(action.recommendation) > 20 else 0.05)
        , 0.99)), 2)),
    },
    {
        "difficulty": "hard",
        "task_description": "Analyze 3 years of trends. Identify top 3 risks in identified_issues.",
        "financial_data": {
            "Year 1": {"revenue": 2100, "CAC": 120},
            "Year 2": {"revenue": 2250, "CAC": 155},
            "Year 3": {"revenue": 2280, "CAC": 198},
        },
        "expected": {
            "top_risks": ["margin", "cac", "opex"],
            "key_numbers": ["51", "198", "1380"],
        },
        "grader": _hard_grader,
    },
]

# ── GLOBAL STATE ──────────────────────────────────────────────────────────────

_current_task = None
_current_state = {"episode_id": str(uuid4()), "step_count": 0}

# ── ENVIRONMENT CLASS ─────────────────────────────────────────────────────────

class FinancialAnalysisEnvironment:
    SUPPORTS_CONCURRENT_SESSIONS: bool = True
    metadata = {"render_modes": []}

    async def reset_async(self, seed=None, options=None): return self.reset(seed, options)
    async def step_async(self, action): return self.step(action)
    def seed(self, seed=None): random.seed(seed)

    def reset(self, seed=None, options=None) -> FinancialAnalysisObservation:
        global _current_task, _current_state
        _current_state = {"episode_id": str(uuid4()), "step_count": 0}
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
        return 0.05 # Baseline fallback

    def close(self): pass
    @property
    def state(self) -> dict: return _current_state