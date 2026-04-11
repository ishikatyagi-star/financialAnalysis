"""Compliance tests for the financial-analysis-env submission.

These mirror what the OpenEnv submission validator checks:
  1. YAML schema: tasks listed under metadata.tasks (not top-level)
  2. Reward range: declared bounds make sense
  3. Grader outputs: all graders return floats strictly in (0, 1)
"""

import sys
import os
import yaml
import importlib

sys.path.insert(0, ".")


def log(msg):
    print(f"[TEST] {msg}")


def run_test_yaml_schema():
    log("Checking openenv.yaml schema...")
    with open("openenv.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Required top-level fields
    assert "name" in config, "Missing 'name'"
    assert "entrypoint" in config, "Missing 'entrypoint'"
    assert "description" in config, "Missing 'description'"

    # Tasks must live under metadata.tasks (matches the framework's task-discovery path)
    metadata = config.get("metadata", {})
    tasks = metadata.get("tasks", [])
    assert len(tasks) >= 3, (
        f"Expected at least 3 tasks under metadata.tasks, found {len(tasks)}. "
        "The submission validator reads tasks from metadata.tasks, not from a "
        "top-level tasks: block."
    )
    for task in tasks:
        assert isinstance(task, str), (
            f"Each entry in metadata.tasks must be a plain string task ID, got {type(task)}"
        )
    log(f"metadata.tasks contains {len(tasks)} tasks: {tasks}")
    log("YAML schema OK.")


def run_test_reward_range():
    log("Checking reward_range...")
    with open("openenv.yaml", "r") as f:
        config = yaml.safe_load(f)
    reward_range = config.get("metadata", {}).get("reward_range", [])
    assert len(reward_range) == 2, "metadata.reward_range must have 2 elements"
    assert reward_range[0] >= 0.0, f"Min reward {reward_range[0]} must be >= 0.0"
    assert reward_range[1] <= 1.0, f"Max reward {reward_range[1]} must be <= 1.0"
    assert reward_range[0] < reward_range[1], "reward_range lower must be < upper"
    log("Reward range OK.")


def run_test_grader_outputs():
    """Graders are tested directly — they are not referenced from YAML grader fields."""
    log("Checking grader outputs for strict (0, 1) range...")

    from financial_analysis_env import grade_easy, grade_medium, grade_hard, grade_expert
    from financial_analysis_env.models import FinancialAnalysisAction

    graders = {
        "easy":   grade_easy,
        "medium": grade_medium,
        "hard":   grade_hard,
        "expert": grade_expert,
    }

    edge_cases = [
        FinancialAnalysisAction(),                                    # empty
        FinancialAnalysisAction(analysis="A" * 1000,
                                identified_issues=["issue1"],
                                recommendation="R" * 1000),          # large
        None,                                                         # None input
    ]

    for task_id, grader_func in graders.items():
        log(f"Testing grader for task: {task_id}")
        for i, case in enumerate(edge_cases):
            try:
                score = grader_func(case)
                assert isinstance(score, float), (
                    f"Grader '{task_id}' returned {type(score)} instead of float"
                )
                assert 0.0 < score < 1.0, (
                    f"Grader '{task_id}' returned {score} for case {i}, "
                    "which is out of strict range (0, 1)"
                )
            except AssertionError:
                raise
            except Exception as e:
                print(f"ERROR: Grader '{task_id}' raised {type(e).__name__}: {e}")
                sys.exit(1)
    log("Grader outputs OK.")


def run_test_task_routing():
    """Ensure reset(task=X) routes to distinct task descriptions."""
    log("Checking task routing...")
    from server.financial_analysis_environment import FinancialAnalysisOpenEnv

    with open("openenv.yaml", "r") as f:
        config = yaml.safe_load(f)
    task_ids = config.get("metadata", {}).get("tasks", [])

    env = FinancialAnalysisOpenEnv()
    seen = {}
    for tid in task_ids:
        obs = env.reset(task=tid)
        seen[tid] = obs.task_description[:60]

    unique = set(seen.values())
    assert len(unique) == len(task_ids), (
        f"Expected {len(task_ids)} distinct task descriptions, got {len(unique)}.\n"
        f"All task IDs appear to route to the same task.\n"
        f"Descriptions: {seen}"
    )
    log(f"Task routing OK ({len(task_ids)} distinct tasks).")
    
    # Check reward in reset logic (MUST be float in (0, 1))
    log("Checking reward value in reset() response...")
    for tid in task_ids:
        obs = env.reset(task=tid)
        assert isinstance(obs.reward, float), f"reset({tid}).reward must be a float, got {type(obs.reward)}"
        assert 0.0 < obs.reward < 1.0, f"reset({tid}).reward {obs.reward} out of range (0, 1)"
    log("Reset reward OK.")

    # Check graders discovery
    log("Checking graders attribute discovery...")
    assert hasattr(env, "graders"), "Environment missing 'graders' property"
    graders = env.graders
    assert isinstance(graders, dict), f"env.graders must be a dict, got {type(graders)}"
    for tid in task_ids:
        assert tid in graders, f"Task '{tid}' missing from env.graders"
        assert callable(graders[tid]), f"Grader for '{tid}' must be callable"
    log(f"Graders discovery OK for {len(graders)} tasks.")


if __name__ == "__main__":
    try:
        run_test_yaml_schema()
        run_test_reward_range()
        run_test_grader_outputs()
        run_test_task_routing()
        print("\n[SUCCESS] All compliance tests passed!")
    except AssertionError as e:
        print(f"\n[FAILURE] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
