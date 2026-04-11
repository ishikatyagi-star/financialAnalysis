#!/usr/bin/env python3
"""Pre-submission validator.

Mirrors the exact checks the OpenEnv submission validator performs:
  1. openenv.yaml schema — tasks under metadata.tasks as a string list
  2. Grader imports and score bounds — direct import, no YAML grader paths needed
  3. Task routing — reset(task=X) produces distinct observations
  4. Task score in info — step() sets info["task_score"] in (0, 1)

Usage:
    python scripts/validate_submission.py
"""

import sys
import importlib

sys.path.insert(0, ".")


def _ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)


# ── Check 1: YAML schema ──────────────────────────────────────────────────────

def check_yaml_schema() -> list:
    import yaml

    with open("openenv.yaml") as f:
        cfg = yaml.safe_load(f)

    # Required top-level fields
    for field in ("name", "entrypoint", "description"):
        assert field in cfg, f"openenv.yaml missing required field '{field}'"

    # Tasks must be under metadata.tasks as a simple string list.
    # The submission validator reads from this path — NOT from a top-level tasks: block.
    metadata = cfg.get("metadata", {})
    tasks = metadata.get("tasks", [])
    assert len(tasks) >= 3, (
        f"metadata.tasks must have ≥3 entries; found {len(tasks)}. "
        "Move task IDs into metadata.tasks as plain strings."
    )
    for t in tasks:
        assert isinstance(t, str), (
            f"Each entry in metadata.tasks must be a plain string; got {type(t)}: {t!r}"
        )

    rr = metadata.get("reward_range", [])
    assert len(rr) == 2, "metadata.reward_range must have exactly 2 elements"
    assert rr[0] >= 0.0, f"reward_range lower bound {rr[0]} must be >= 0.0"
    assert rr[1] <= 1.0, f"reward_range upper bound {rr[1]} must be <= 1.0"

    _ok(f"YAML schema valid: metadata.tasks={tasks}, reward_range={rr}")
    return tasks


# ── Check 2: Grader imports and score bounds ──────────────────────────────────

def check_grader_scores(task_ids: list) -> None:
    from financial_analysis_env import grade_easy, grade_medium, grade_hard, grade_expert
    from financial_analysis_env.models import FinancialAnalysisAction

    graders = {
        "easy":   grade_easy,
        "medium": grade_medium,
        "hard":   grade_hard,
        "expert": grade_expert,
    }

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

    for tid in task_ids:
        assert tid in graders, (
            f"Task '{tid}' listed in metadata.tasks but no grader function found. "
            f"Available: {list(graders)}"
        )
        fn = graders[tid]
        for input_name, action in test_inputs:
            score = fn(action)
            assert isinstance(score, float), (
                f"Task '{tid}' grader returned {type(score).__name__} for '{input_name}'"
            )
            assert score != 0.0, (
                f"Task '{tid}' grader returned exactly 0.0 for input '{input_name}'"
            )
            assert score != 1.0, (
                f"Task '{tid}' grader returned exactly 1.0 for input '{input_name}'"
            )
            assert 0.0 < score < 1.0, (
                f"Task '{tid}' grader returned {score} for '{input_name}' — "
                "must be strictly inside (0, 1)"
            )
        _ok(f"Grader '{tid}': all {len(test_inputs)} input types return valid scores in (0, 1)")


# ── Check 3: Task routing ─────────────────────────────────────────────────────

def check_task_routing(task_ids: list) -> None:
    from server.financial_analysis_environment import FinancialAnalysisOpenEnv

    env = FinancialAnalysisOpenEnv()
    seen = {}

    for tid in task_ids:
        obs = env.reset(task=tid)
        assert obs.task_description, f"Task '{tid}': reset() returned empty task_description"
        seen[tid] = obs.task_description[:60]

    unique = set(seen.values())
    assert len(unique) == len(task_ids), (
        f"Expected {len(task_ids)} distinct task descriptions, got {len(unique)}.\n"
        f"All task IDs appear to be routing to the same task.\n"
        f"Descriptions: {seen}"
    )
    _ok(f"Task routing: all {len(task_ids)} task IDs produce distinct observations")


# ── Check 4: task_score in step info ─────────────────────────────────────────

def check_step_task_score(task_ids: list) -> None:
    from server.financial_analysis_environment import FinancialAnalysisOpenEnv
    from financial_analysis_env.models import FinancialAnalysisAction

    env = FinancialAnalysisOpenEnv()
    probe = FinancialAnalysisAction(
        analysis="Q2 revenue grew 20.8%. Month 8 anomaly 310. Gross margin 51%. "
                 "Cash runway 8 months, covenant risk. CAC rose from 4.7 to 7.9.",
        identified_issues=["margin decline", "cac increase", "opex growth"],
        recommendation="Investigate anomaly, reduce CAC, sustain Q2 growth.",
    )

    for tid in task_ids:
        obs = env.reset(task=tid)
        result = env.step(probe)

        assert result.done, f"Task '{tid}': step() must return done=True for single-turn env"
        assert result.reward is not None, f"Task '{tid}': step() returned reward=None"
        assert isinstance(result.reward, float), (
            f"Task '{tid}': reward must be float, got {type(result.reward)}"
        )
        assert 0.0 < result.reward < 1.0, (
            f"Task '{tid}': reward {result.reward} is not strictly in (0, 1)"
        )

        task_score = result.info.get("task_score")
        assert task_score is not None, (
            f"Task '{tid}': info['task_score'] is missing from step() response"
        )
        assert isinstance(task_score, float), (
            f"Task '{tid}': info['task_score'] must be float, got {type(task_score)}"
        )
        assert 0.0 < task_score < 1.0, (
            f"Task '{tid}': info['task_score']={task_score} is not strictly in (0, 1)"
        )
        _ok(f"Task '{tid}': step() done=True, reward={result.reward:.4f}, "
            f"task_score={task_score:.4f}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("OpenEnv Pre-Submission Validator")
    print("=" * 60)

    try:
        task_ids = check_yaml_schema()
        check_grader_scores(task_ids)
        check_task_routing(task_ids)
        check_step_task_score(task_ids)

        print()
        print("=" * 60)
        print("[PASS] All pre-submit checks passed. Safe to submit.")
        print("=" * 60)

    except AssertionError as exc:
        print()
        _fail(str(exc))
        print()
        print("[FAIL] Pre-submit validation failed. Fix the issue above before submitting.")
        sys.exit(1)

    except Exception as exc:
        import traceback
        print()
        _fail(f"Unexpected error: {exc}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
