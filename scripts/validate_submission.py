#!/usr/bin/env python3
"""Pre-submission validator.

Run this locally before every resubmit. It mirrors the exact checks the
OpenEnv validator performs, so a local PASS means the submission is safe
to push.

Usage:
    python scripts/validate_submission.py
"""

import sys
import importlib

sys.path.insert(0, ".")


def _log_ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def _log_fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)


# ── Check 1: YAML schema ──────────────────────────────────────────────────────

def check_yaml_schema() -> list:
    import yaml

    with open("openenv.yaml") as f:
        cfg = yaml.safe_load(f)

    tasks = cfg.get("tasks", [])
    assert len(tasks) >= 3, f"Need ≥3 tasks, found {len(tasks)}"

    required_fields = {"id", "name", "description", "grader"}
    for t in tasks:
        missing = required_fields - t.keys()
        assert not missing, f"Task '{t.get('id', '?')}' missing fields: {missing}"
        assert ":" in t["grader"], (
            f"Task '{t['id']}' grader path '{t['grader']}' must use module:function format"
        )

    rr = cfg.get("metadata", {}).get("reward_range", [])
    assert len(rr) == 2, "metadata.reward_range must have exactly 2 elements"
    assert rr[0] >= 0.0, f"reward_range lower bound {rr[0]} must be >= 0.0"
    assert rr[1] <= 1.0, f"reward_range upper bound {rr[1]} must be <= 1.0"
    assert rr[0] < rr[1], "reward_range lower must be < upper"

    _log_ok(f"YAML schema valid: {len(tasks)} tasks, reward_range={rr}")
    return tasks


# ── Check 2: Grader imports ───────────────────────────────────────────────────

def check_grader_imports(tasks: list) -> list:
    grader_fns = []
    for t in tasks:
        mod_name, fn_name = t["grader"].split(":", 1)
        try:
            mod = importlib.import_module(mod_name)
        except ImportError as exc:
            raise AssertionError(
                f"Task '{t['id']}': cannot import module '{mod_name}': {exc}"
            ) from exc
        fn = getattr(mod, fn_name, None)
        assert fn is not None, (
            f"Task '{t['id']}': module '{mod_name}' has no attribute '{fn_name}'"
        )
        assert callable(fn), f"Task '{t['id']}': '{fn_name}' is not callable"
        grader_fns.append((t["id"], fn))
        _log_ok(f"Grader import '{t['grader']}': OK")
    return grader_fns


# ── Check 3: Score range for multiple input types ─────────────────────────────

def check_grader_scores(grader_fns: list) -> None:
    from financial_analysis_env.models import FinancialAnalysisAction

    test_inputs = [
        ("none",         None),
        ("empty_dict",   {}),
        ("empty_action", FinancialAnalysisAction()),
        ("probe_action", FinancialAnalysisAction(
            analysis="probe",
            identified_issues=["probe issue"],
            recommendation="probe recommendation",
        )),
    ]

    for task_id, fn in grader_fns:
        for input_name, action in test_inputs:
            score = fn(action)
            assert isinstance(score, float), (
                f"Task '{task_id}' with input '{input_name}': returned {type(score).__name__}, expected float"
            )
            assert score != 0.0, (
                f"Task '{task_id}' with input '{input_name}': score is exactly 0.0 (invalid)"
            )
            assert score != 1.0, (
                f"Task '{task_id}' with input '{input_name}': score is exactly 1.0 (invalid)"
            )
            assert 0.0 < score < 1.0, (
                f"Task '{task_id}' with input '{input_name}': score {score} is outside open interval (0, 1)"
            )
        _log_ok(f"Grader '{task_id}': all {len(test_inputs)} input types return valid scores in (0, 1)")


# ── Check 4: Task routing (reset respects task_id) ────────────────────────────

def check_task_routing(tasks: list) -> None:
    from server.financial_analysis_environment import FinancialAnalysisOpenEnv

    env = FinancialAnalysisOpenEnv()
    seen_descriptions = {}

    for t in tasks:
        obs = env.reset(task_id=t["id"])
        desc = obs.task_description
        assert desc, f"Task '{t['id']}': reset() returned empty task_description"
        seen_descriptions[t["id"]] = desc[:60]

    # Verify that different task IDs produce different task descriptions
    unique_descs = set(seen_descriptions.values())
    assert len(unique_descs) == len(tasks), (
        f"Expected {len(tasks)} distinct task descriptions but got {len(unique_descs)}.\n"
        f"All tasks appear to be routing to the same task — check reset(task_id=...) handling.\n"
        f"Descriptions: {seen_descriptions}"
    )
    _log_ok(f"Task routing: all {len(tasks)} task IDs produce distinct observations")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("OpenEnv Pre-Submission Validator")
    print("=" * 60)

    try:
        tasks = check_yaml_schema()
        grader_fns = check_grader_imports(tasks)
        check_grader_scores(grader_fns)
        check_task_routing(tasks)

        print()
        print("=" * 60)
        print("[PASS] All pre-submit checks passed. Safe to submit.")
        print("=" * 60)

    except AssertionError as exc:
        print()
        _log_fail(str(exc))
        print()
        print("[FAIL] Pre-submit validation failed. Fix the issue above before submitting.")
        sys.exit(1)

    except Exception as exc:
        print()
        _log_fail(f"Unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
