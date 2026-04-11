import uvicorn
import yaml
from pathlib import Path
from uuid import uuid4
from typing import Any, Dict
from pydantic import BaseModel
from openenv.core.env_server import create_app
from financial_analysis_env.models import FinancialAnalysisAction, FinancialAnalysisObservation
from financial_analysis_env.environment import (
    FinancialAnalysisEnvironment, TASKS,
    grade_easy, grade_medium, grade_hard,
)

app = create_app(
    FinancialAnalysisEnvironment,
    action_cls=FinancialAnalysisAction,
    observation_cls=FinancialAnalysisObservation,
    env_name="financial-analysis-env",
)

# Remove the default routes we are overriding so our custom
# /tasks, /metadata, /health, / endpoints take precedence.
routes_to_keep = []
for route in app.routes:
    if hasattr(route, "path") and route.path in ["/", "/tasks", "/metadata", "/health"]:
        continue
    routes_to_keep.append(route)
app.routes = routes_to_keep

# ── Load openenv.yaml for metadata ────────────────────────────────────────────
_YAML_PATH = Path(__file__).resolve().parent.parent / "openenv.yaml"
try:
    with open(_YAML_PATH) as f:
        _OPENENV_META = yaml.safe_load(f)
except Exception:
    _OPENENV_META = {
        "name": "financial-analysis-env",
        "description": "RL environment for financial analysis tasks",
    }

# Grader map: task id → bare-float grader callable (matches openenv.yaml paths)
_GRADERS: Dict[str, Any] = {
    "easy":   grade_easy,
    "medium": grade_medium,
    "hard":   grade_hard,
}


@app.get("/")
def root():
    return {"message": "Financial Analysis OpenEnv server running"}


@app.get("/metadata")
def metadata():
    return {
        "name":        _OPENENV_META.get("name", "financial-analysis-env"),
        "description": _OPENENV_META.get("description", "RL environment for financial analysis tasks"),
    }


@app.get("/tasks")
def list_tasks():
    """All 3 tasks with grader info — IDs match openenv.yaml."""
    return {
        "tasks": [
            {
                "id":               t["difficulty"],
                "difficulty":       t["difficulty"],
                "description":      t["task_description"],
                "has_grader":       True,
                "grader":           f"financial_analysis_env.environment.grade_{t['difficulty']}",
                "grader_endpoint":  f"/grade/{t['difficulty']}",
            }
            for t in TASKS
        ],
        "total":               len(TASKS),
        "tasks_with_graders":  len(TASKS),
    }


@app.get("/health")
def health():
    return {"status": "healthy", "tasks_with_graders": len(TASKS)}


# ── /grade/{task_id} — direct, stateless, deterministic grading ───────────────
# Bypasses the stateless reset/step routing problem entirely.
# The checker can POST an action here with the task_id and get a score.

class GradeRequest(BaseModel):
    action: Dict[str, Any]


@app.post("/grade/{task_id}")
def grade_task(task_id: str, body: GradeRequest):
    """Grade an action against a specific task. Returns score strictly in (0,1)."""
    if task_id not in _GRADERS:
        return {"error": f"Unknown task_id '{task_id}'. Use: easy, medium, hard"}
    try:
        action = FinancialAnalysisAction.model_validate(body.action)
        score  = _GRADERS[task_id](action)
        return {
            "task_id":  task_id,
            "score":    score,
            "in_range": 0.0 < score < 1.0,
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/grade")
def grade_all(body: GradeRequest):
    """Grade an action against all 3 tasks — useful for smoke-testing."""
    results = {}
    for task_id, grader in _GRADERS.items():
        try:
            action = FinancialAnalysisAction.model_validate(body.action)
            score  = grader(action)
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
            tid   = task["difficulty"]
            score = _GRADERS[tid](test_action)
            results.append({
                "task_id":       tid,
                "task_index":    i,
                "difficulty":    tid,
                "reward":        score,
                "done":          True,
                "reward_in_range": 0.0 < score < 1.0,
            })
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
