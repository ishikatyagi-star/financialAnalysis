import importlib
import inspect
import yaml
import sys
import os

sys.path.insert(0, ".")

with open("openenv.yaml") as f:
    config = yaml.safe_load(f)

tasks = config.get("tasks", [])
print(f"Found {len(tasks)} tasks in openenv.yaml")

for task in tasks:
    grader_path = task.get("grader", "")
    tid = task.get("id", "unknown")
    print(f"\nTask: {tid}")
    print(f"  grader path: {grader_path}")

    # Try colon syntax (module:function)
    if ":" in grader_path:
        module_path, func_name = grader_path.rsplit(":", 1)
    elif "." in grader_path:
        module_path, func_name = grader_path.rsplit(".", 1)
    else:
        print("  ERROR: Invalid grader path format")
        continue

    print(f"  module: {module_path}, function: {func_name}")

    try:
        mod = importlib.import_module(module_path)
        func = getattr(mod, func_name)
        print(f"  LOADED OK: {func}")
        sig = inspect.signature(func)
        print(f"  Signature: {sig}")
        print(f"  Parameters: {list(sig.parameters.keys())}")
    except Exception as e:
        print(f"  IMPORT FAILED: {type(e).__name__}: {e}")

# Also test calling the graders
print("\n\n=== Testing grader calls ===")
from financial_analysis_env.models import FinancialAnalysisAction
from financial_analysis_env.environment import grade_easy, grade_medium, grade_hard, grade_expert

action = FinancialAnalysisAction(
    analysis="Q2 is the best quarter with 20.83% growth",
    identified_issues=["Q2 best quarter"],
    recommendation="Continue investing in Q2 summer promotions to replicate success"
)

for name, func in [("grade_easy", grade_easy), ("grade_medium", grade_medium), ("grade_hard", grade_hard), ("grade_expert", grade_expert)]:
    try:
        result = func(action)
        print(f"{name}(action) = {result} (type={type(result).__name__})")
        print(f"  In range (0,1): {0 < result < 1}")
    except Exception as e:
        print(f"{name} FAILED: {type(e).__name__}: {e}")
