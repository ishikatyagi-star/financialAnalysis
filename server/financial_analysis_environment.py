"""OpenEnv-compatible wrapper for FinancialAnalysisEnvironment.

The entrypoint in openenv.yaml points here,
so the OpenEnv framework can natively wrap this class and discover tasks
from the class metadata.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
import random
from uuid import uuid4
from typing import Any

from financial_analysis_env.models import (
    FinancialAnalysisAction,
    FinancialAnalysisObservation,
)
from financial_analysis_env.environment import (
    FinancialAnalysisEnvironment,
    TASKS,
    grade_easy,
    grade_medium,
    grade_hard,
    grade_expert,
    _clamp,
)


class EnvironmentState(BaseModel):
    episode_id: str = ""
    step_count: int = 0

class FinancialAnalysisOpenEnv:
    """Native environment class for the OpenEnv framework.

    This is what the openenv.yaml entrypoint points to.
    The framework wraps this class natively and pulls the task list
    directly from class metadata without needing custom HTTP routes.
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        self._env = FinancialAnalysisEnvironment()
        self._step_count = 0

    def reset(
        self,
        seed: int | None = None,
        task: str = "easy",
        **kwargs: object,
    ) -> FinancialAnalysisObservation:
        if seed is not None:
            random.seed(seed)

        # Select task by id
        task_map = {"easy": 0, "medium": 1, "hard": 2, "expert": 3}
        task_idx = task_map.get(task, 0)
        task_data = TASKS[task_idx]
        self._env._current_task = task_data
        self._env._episode_id = str(uuid4())
        self._env._step_count = 0
        self._step_count = 0

        return FinancialAnalysisObservation(
            task_description=task_data["task_description"],
            financial_data=task_data["financial_data"],
            difficulty=task_data["difficulty"],
            done=False,
            reward=None,
        )

    async def reset_async(
        self,
        seed: int | None = None,
        task: str = "easy",
        **kwargs: object,
    ) -> FinancialAnalysisObservation:
        return self.reset(seed, task, **kwargs)

    def step(
        self, action: FinancialAnalysisAction, **kwargs: object
    ) -> FinancialAnalysisObservation:
        self._step_count += 1

        if self._env._current_task is None:
            self._env._current_task = TASKS[0]

        task_data = self._env._current_task

        try:
            reward, breakdown = task_data["grader"](action, task_data["expected"])
        except Exception:
            reward = _clamp(0.02)
            breakdown = {"error": "grader_exception", "success": False}

        return FinancialAnalysisObservation(
            task_description=task_data["task_description"],
            financial_data=task_data["financial_data"],
            difficulty=task_data["difficulty"],
            done=True,
            reward=reward,
        )

    async def step_async(
        self, action: FinancialAnalysisAction, **kwargs: object
    ) -> FinancialAnalysisObservation:
        return self.step(action, **kwargs)

    @property
    def state(self) -> EnvironmentState:
        return EnvironmentState(
            episode_id=self._env._episode_id,
            step_count=self._step_count,
        )

    def close(self) -> None:
        self._env._current_task = None
