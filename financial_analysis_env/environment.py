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
    reward += 0.05 * min(sum(1 for w in ["because", "due to", "driven by", "as a result"] if w in analysis), 2)
    return round(max(0.0, min(reward, 1.0)), 2)

# ── TASK DEFINITIONS ──────────────────────────────────────────────────────────

TASKS = [
    {
        "difficulty": "easy",
        "task_description": (...),
        "financial_data": {...},
        "expected": {
            "best_quarter": "Q2",
            "growth_pct": 20.8,
        },
        "grader": lambda action, expected: (
            (0.4 if "q2" in " ".join(i.lower() for i in action.identified_issues) else 0.0) +
            (0.3 if any(x in action.analysis.lower() for x in ["20.8", "20%", "21%"]) else 0.0) +
            (0.3 if len(action.recommendation) > 20 else 0.0)
        ),
    },
    {
        "difficulty": "medium",
        "task_description": (...),
        "financial_data": {...},
        "expected": {
            "anomaly_month": "Month 8",
        },
        "grader": lambda action, expected: (
            (0.4 if "month 8" in " ".join(i.lower() for i in action.identified_issues) else 0.0) +
            (0.3 if any(w in action.analysis.lower() for w in ["spike", "anomaly", "unusual"]) else 0.0) +
            (0.3 if any(w in action.recommendation.lower() for w in ["investigate", "audit", "review", "check"]) else 0.0)
        ),
    },
    {
        "difficulty": "hard",
        "task_description": (...),
        "financial_data": {...},
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
            "step_count": 0
        }
        # Explicitly choosing tasks in order can sometimes help validators see variety faster
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