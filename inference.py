"""
Baseline inference script for the Financial Analysis Environment.

Runs all 3 tasks deterministically against an LLM and reports scores.

Usage:
    OPENAI_API_KEY=sk-... python inference.py
    OPENAI_API_KEY=sk-... MODEL_NAME=gpt-4o python inference.py

    # HuggingFace router (alternative backend):
    HF_TOKEN=hf_... API_BASE_URL=https://router.huggingface.co/v1 \\
        MODEL_NAME=Qwen/Qwen2.5-72B-Instruct python inference.py
"""

import os
import json
import re
from typing import List
from openai import OpenAI

from financial_analysis_env.environment import FinancialAnalysisEnvironment, TASKS
from financial_analysis_env.models import FinancialAnalysisAction

# ── CONSTANTS ──────────────────────────────────────────────────────────────────

TASK_NAME         = "financial_analysis"
BENCHMARK         = "financial_analysis_env"
SUCCESS_THRESHOLD = 0.5


# ── LOGGING ────────────────────────────────────────────────────────────────────

def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step, action, reward, done, error=None):
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success, steps, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}",
        flush=True,
    )


# ── LLM CALL ───────────────────────────────────────────────────────────────────

def get_model_response(client: OpenAI, task_description: str, financial_data: dict) -> dict:
    prompt = f"""You are a financial analyst.

Task:
{task_description}

Data:
{json.dumps(financial_data, indent=2)}

Respond ONLY with a JSON object (no markdown, no explanation):
{{
  "identified_issues": ["issue 1", "issue 2", "issue 3"],
  "analysis": "detailed analysis citing specific numbers...",
  "recommendation": "specific actionable recommendation..."
}}"""

    text = ""
    try:
        completion = client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,   # reproducible
            max_tokens=600,
        )
        text = (completion.choices[0].message.content or "").strip()
        text = re.sub(r"```json|```", "", text).strip()
        return json.loads(text)
    except Exception:
        # Try extracting JSON from messy output
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {
            "identified_issues": [],
            "analysis": text or "no response",
            "recommendation": "",
        }


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    # Credentials — OPENAI_API_KEY required by spec; HF_TOKEN accepted as fallback
    api_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("HF_TOKEN")
        or os.getenv("API_KEY")
    )
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required.\n"
            "Set it with: export OPENAI_API_KEY=sk-..."
        )

    api_base = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
    model    = os.getenv("MODEL_NAME",   "gpt-4o-mini")

    client = OpenAI(base_url=api_base, api_key=api_key)

    all_rewards: List[float] = []

    log_start(task=TASK_NAME, env=BENCHMARK, model=model)

    # Iterate all 3 tasks deterministically — guaranteed coverage, reproducible
    for i, task in enumerate(TASKS):
        step_num = i + 1
        try:
            # Pin the task directly so we don't rely on random selection
            env = FinancialAnalysisEnvironment()
            env._current_task = task
            env._episode_id   = f"episode-{task['difficulty']}"
            env._step_count   = 0

            action_dict = get_model_response(
                client,
                task["task_description"],
                task["financial_data"],
            )
            action = FinancialAnalysisAction(**action_dict)
            result = env.step(action)

            reward = result.reward if result.reward is not None else 0.02
            done   = result.done
            all_rewards.append(reward)

            log_step(
                step=step_num,
                action=f"financial_analysis_{task['difficulty']}",
                reward=reward,
                done=done,
            )
            env.close()

        except Exception as e:
            # Floor at 0.02 so error steps are still strictly in (0, 1)
            all_rewards.append(0.02)
            log_step(
                step=step_num,
                action="error",
                reward=0.02,
                done=True,
                error=str(e).replace("\n", " "),
            )

    success = all(r >= SUCCESS_THRESHOLD for r in all_rewards)
    log_end(success=success, steps=len(all_rewards), rewards=all_rewards)


if __name__ == "__main__":
    main()
