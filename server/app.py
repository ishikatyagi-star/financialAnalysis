import uvicorn
import yaml
from pathlib import Path
from uuid import uuid4
from openenv.core.env_server import create_fastapi_app
from financial_analysis_env.models import FinancialAnalysisAction, FinancialAnalysisObservation
from financial_analysis_env.environment import FinancialAnalysisEnvironment, TASKS, grade_easy, grade_medium, grade_hard

app = create_fastapi_app(
    FinancialAnalysisEnvironment,
    action_cls=FinancialAnalysisAction,
    observation_cls=FinancialAnalysisObservation
)

# ── Load openenv.yaml for metadata ────────────────────────────────────────────
_YAML_PATH = Path(__file__).resolve().parent.parent / "openenv.yaml"
try:
    with open(_YAML_PATH) as f:
        _OPENENV_META = yaml.safe_load(f)
except Exception:
    _OPENENV_META = {"name": "financial-analysis-env", "description": "RL environment for financial analysis tasks"}

# Grader map matching openenv.yaml task ids → actual callable graders
_GRADER_MAP = {
    "easy": {"module": "financial_analysis_env.environment.grade_easy", "fn": grade_easy},
    "medium": {"module": "financial_analysis_env.environment.grade_medium", "fn": grade_medium},
    "hard": {"module": "financial_analysis_env.environment.grade_hard", "fn": grade_hard},
}

@app.get("/")
def root():
    return {"message": "OpenEnv server running"}

@app.get("/metadata")
def metadata():
    return {
        "name": _OPENENV_META.get("name", "financial-analysis-env"),
        "description": _OPENENV_META.get("description", "RL environment for financial analysis tasks"),
    }

@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "id": t["difficulty"],
                "name": t.get("task_description", "")[:60],
                "difficulty": t["difficulty"],
                "description": t["task_description"],
                "has_grader": True,
                "grader": _GRADER_MAP[t["difficulty"]]["module"],
            }
            for t in TASKS
        ],
        "total": len(TASKS),
        "tasks_with_graders": len(TASKS),
    }

@app.get("/health")
def health():
    return {"status": "healthy", "tasks_with_graders": len(TASKS)}

@app.get("/run_test")
def run_test():
    try:
        results = []
        # Force each task directly instead of relying on random seeds
        for i, task in enumerate(TASKS):
            env = FinancialAnalysisEnvironment()
            env._current_task = task  # force the specific task
            env._episode_id = str(uuid4())
            env._step_count = 0

            action = FinancialAnalysisAction(
                analysis="Test analysis of financial data with some numbers.",
                identified_issues=["test issue one", "test issue two", "test issue three"],
                recommendation="Perform a deeper audit of the financial metrics."
            )
            result = env.step(action)
            results.append({
                "task_index": i,
                "difficulty": task["difficulty"],
                "reward": result.reward,
                "done": result.done,
                "reward_in_range": 0.0 < result.reward < 1.0
            })

        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()