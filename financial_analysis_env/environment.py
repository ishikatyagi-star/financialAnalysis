import random
from uuid import uuid4
from typing import Optional, Any # Added for type safety

try:
    from .models import FinancialAnalysisAction, FinancialAnalysisObservation
except ImportError:
    from models import FinancialAnalysisAction, FinancialAnalysisObservation

# ... RISK_KEYWORDS and TASKS remain the same ...

class FinancialAnalysisEnvironment:
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    # FIX 1: Add 'seed' and 'options' arguments. 
    # OpenEnv calls reset(seed=..., options=...). If these are missing, it crashes.
    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> FinancialAnalysisObservation:
        global _current_task, _current_state

        if seed is not None:
            random.seed(seed)

        _current_state = {"episode_id": str(uuid4()), "step_count": 0}
        
        # FIX 2: Check if an episode_id was passed in the options
        if options and "episode_id" in options:
            _current_state["episode_id"] = options["episode_id"]

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

        # The reward logic below is correct, it stays inside the Observation object
        return FinancialAnalysisObservation(
            task_description=_current_task["task_description"],
            financial_data=_current_task["financial_data"],
            difficulty=_current_task["difficulty"],
            done=True,
            reward=reward,
        )

    def _calculate_reward(self, action: FinancialAnalysisAction) -> float:
        # ... Your reward logic is fine, just ensure it returns a float ...
        # (The code you provided for reward calculation is logically sound)
        
        # Just a snippet to show it stays as a helper:
        task = _current_task
        expected = task["expected"]
        # ... calculation ...
        reward = 0.8 # example
        return round(max(0.0, min(reward, 1.0)), 2)
    
    # FIX 3: Ensure 'async def close' is at the correct indentation (aligned with step)
    async def close(self):
        """Clean up resources. Required by the OpenEnv caller."""
        pass
    
    @property
    def state(self) -> dict:
        return _current_state