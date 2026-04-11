import sys
import os
import yaml
import importlib

# Add current dir to path
sys.path.insert(0, ".")

def log(msg):
    print(f"[TEST] {msg}")

def run_test_yaml_schema():
    log("Checking openenv.yaml schema...")
    with open("openenv.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    assert "tasks" in config, "Missing 'tasks' section"
    tasks = config["tasks"]
    assert len(tasks) >= 3, f"Expected at least 3 tasks, found {len(tasks)}"
    
    for task in tasks:
        tid = task.get("id", "unknown")
        assert "id" in task, "Task missing id"
        assert "name" in task, f"Task {tid} missing name"
        assert "description" in task, f"Task {tid} missing description"
        assert "difficulty" in task, f"Task {tid} missing difficulty"
        assert "grader" in task, f"Task {tid} missing grader"
        assert ":" in task["grader"], f"Task {tid} grader path '{task['grader']}' must use module:function format"
    log("YAML schema OK.")

def run_test_reward_range():
    log("Checking reward_range...")
    with open("openenv.yaml", "r") as f:
        config = yaml.safe_load(f)
    reward_range = config.get("metadata", {}).get("reward_range", [])
    assert len(reward_range) == 2, "metadata.reward_range must have 2 elements"
    assert reward_range[0] >= 0.0, f"Min reward {reward_range[0]} must be >= 0.0"
    assert reward_range[1] <= 1.0, f"Max reward {reward_range[1]} must be <= 1.0"
    assert reward_range[0] < reward_range[1], "reward_range lower must be strictly less than upper"
    log("Reward range OK.")

def run_test_grader_outputs():
    log("Checking grader outputs for strict (0, 1) range...")
    with open("openenv.yaml", "r") as f:
        config = yaml.safe_load(f)
    tasks = config["tasks"]
    
    from financial_analysis_env.models import FinancialAnalysisAction
    edge_cases = [
        FinancialAnalysisAction(), # Empty
        FinancialAnalysisAction(analysis="A"*1000, identified_issues=["issue1"], recommendation="R"*1000), # Large
        {"analysis": "raw dict test"}, # Dict input
        None, # None input
    ]

    for task in tasks:
        grader_path = task["grader"]
        log(f"Testing grader: {grader_path}")
        module_path, func_name = grader_path.split(":")
        mod = importlib.import_module(module_path)
        grader_func = getattr(mod, func_name)
        
        for i, case in enumerate(edge_cases):
            try:
                score = grader_func(case)
                assert isinstance(score, float), f"Grader {grader_path} returned {type(score)} instead of float"
                assert 0.0 < score < 1.0, f"Grader {grader_path} returned {score} for case {i}, which is out of strict range (0, 1)"
            except Exception as e:
                print(f"ERROR: Grader {grader_path} raised {type(e).__name__}: {e}")
                sys.exit(1)
    log("Grader outputs OK.")

if __name__ == "__main__":
    try:
        run_test_yaml_schema()
        run_test_reward_range()
        run_test_grader_outputs()
        print("\n[SUCCESS] All compliance tests passed!")
    except AssertionError as e:
        print(f"\n[FAILURE] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
