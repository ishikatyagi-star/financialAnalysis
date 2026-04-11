"""FastAPI application for the Financial Analysis OpenEnv environment.

- Uses create_app() with a lambda factory (not the class directly)
- Positional args match the library's expected signature
- Custom endpoints are mounted on top (not shadowed)
"""

from __future__ import annotations

import os
import uvicorn
from typing import Any, Dict
from pydantic import BaseModel
import gradio as gr

from openenv.core.env_server.http_server import create_app

from .demo import build_demo
from .financial_analysis_environment import FinancialAnalysisOpenEnv
from financial_analysis_env.models import (
    FinancialAnalysisAction,
    FinancialAnalysisObservation,
)
from financial_analysis_env.environment import (
    TASKS,
    grade_easy,
    grade_medium,
    grade_hard,
    grade_expert,
)


# ── Create the FastAPI app using the same pattern as the reference ────────────
MAX_CONCURRENT = int(os.getenv("FINANCIAL_ENV_MAX_CONCURRENT", "4"))

app = create_app(
    lambda: FinancialAnalysisOpenEnv(),
    FinancialAnalysisAction,
    FinancialAnalysisObservation,
    env_name="financial-analysis-env",
    max_concurrent_envs=MAX_CONCURRENT,
)

# ── Mount Gradio demo UI at the root path ────────────────────────────────────
demo = build_demo()
app = gr.mount_gradio_app(app, demo, path="/")


# ── Grader map ────────────────────────────────────────────────────────────────
_GRADERS: Dict[str, Any] = {
    "easy":   grade_easy,
    "medium": grade_medium,
    "hard":   grade_hard,
    "expert": grade_expert,
}


# ── Startup grader self-check ─────────────────────────────────────────────────
def _verify_graders_at_startup() -> None:
    """Fail fast at import time if any grader is broken or returns a score outside (0, 1)."""
    probe = FinancialAnalysisAction(
        analysis="probe analysis text",
        identified_issues=["probe issue"],
        recommendation="probe recommendation",
    )
    broken = []
    for _tid, grader_fn in _GRADERS.items():
        try:
            score = grader_fn(probe)
            if not isinstance(score, float) or not (0.0 < score < 1.0):
                broken.append(f"{_tid}: returned {score!r}")
        except Exception as exc:
            broken.append(f"{_tid}: raised {exc}")
    if broken:
        raise RuntimeError(
            "Grader self-check FAILED — fix before deploying:\n"
            + "\n".join(f"  • {b}" for b in broken)
        )


_verify_graders_at_startup()


# ── /grade/{task_id} — direct, stateless grading ─────────────────────────────

class GradeRequest(BaseModel):
    action: Dict[str, Any]


@app.post("/grade/{task_id}")
def grade_task(task_id: str, body: GradeRequest):
    """Grade an action against a specific task. Returns score strictly in (0,1)."""
    if task_id not in _GRADERS:
        return {"error": f"Unknown task_id '{task_id}'. Use: easy, medium, hard"}
    try:
        action = FinancialAnalysisAction.model_validate(body.action)
        score = _GRADERS[task_id](action)
        return {
            "task_id": task_id,
            "score": score,
            "in_range": 0.0 < score < 1.0,
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/grade")
def grade_all(body: GradeRequest):
    """Grade an action against all 3 tasks."""
    results = {}
    for task_id, grader in _GRADERS.items():
        try:
            action = FinancialAnalysisAction.model_validate(body.action)
            score = grader(action)
            results[task_id] = {"score": score, "in_range": 0.0 < score < 1.0}
        except Exception as e:
            results[task_id] = {"error": str(e)}
    return results


# ── /run_test — smoke test all 3 graders ─────────────────────────────────────
@app.get("/run_test")
def run_test():
    try:
        test_action = FinancialAnalysisAction(
            analysis="Test analysis of financial data with some numbers.",
            identified_issues=["test issue one", "test issue two", "test issue three"],
            recommendation="Perform a deeper audit of the financial metrics.",
        )
        results = []
        for i, task in enumerate(TASKS):
            tid = task["difficulty"]
            score = _GRADERS[tid](test_action)
            results.append({
                "task_id": tid,
                "task_index": i,
                "difficulty": tid,
                "reward": score,
                "done": True,
                "reward_in_range": 0.0 < score < 1.0,
            })
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
