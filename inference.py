import os
import json
import re
import sys
from typing import List
from openai import OpenAI

from financial_analysis_env.environment import FinancialAnalysisEnvironment
from financial_analysis_env.models import FinancialAnalysisAction

# ── CONFIG ────────────────────────────────────────────────────────────────────

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is required")

TASK_NAME  = "financial_analysis"
BENCHMARK  = "financial_analysis_env"
SUCCESS_THRESHOLD = 0.5

# ── LOGGING ───────────────────────────────────────────────────────────────────

def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error=None):
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error if error else 'null'}",
        flush=True
    )

def log_end(success, steps, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}",
        flush=True
    )

# ── LLM CALL ──────────────────────────────────────────────────────────────────

def get_model_response(client: OpenAI, task_description: str, financial_data: dict) -> dict:
    prompt = f"""You are a financial analyst.

Task:
{task_description}

Data:
{json.dumps(financial_data, indent=2)}

Respond ONLY with a JSON object, no markdown, no explanation:
{{
  "identified_issues": ["issue 1", "issue 2", "issue 3"],
  "analysis": "detailed analysis citing specific numbers...",
  "recommendation": "specific actionable recommendation..."
}}"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,   # reproducible
            max_tokens=600,
        )
        text = (completion.choices[0].message.content or "").strip()
        text = re.sub(r"```json|```", "", text).strip()
        return json.loads(text)
    except Exception as e:
        # Try extracting JSON from messy output
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {
            "identified_issues": [],
            "analysis": f"Parse error: {e}",
            "recommendation": "",
        }

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    # Import TASKS directly to iterate all 3 deterministically
    from financial_analysis_env.environment import TASKS

    all_rewards: List[float] = []
    total_steps = 0

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    for i, task in enumerate(TASKS):
        step_num = i + 1
        try:
            # Force each task directly — no random.choice
            env = FinancialAnalysisEnvironment()
            env._current_task = task
            env._episode_id   = f"episode-{task['difficulty']}"
            env._step_count   = 0

            action_dict = get_model_response(client, task["task_description"], task["financial_data"])
            action      = FinancialAnalysisAction(**action_dict)
            result      = env.step(action)

            reward = result.reward or 0.0
            done   = result.done
            all_rewards.append(reward)
            total_steps += 1

            log_step(
                step=step_num,
                action=f"financial_analysis_{task['difficulty']}",
                reward=reward,
                done=done,
            )
            env.close()

        except Exception as e:
            all_rewards.append(0.0)
            total_steps += 1
            log_step(
                step=step_num,
                action="error",
                reward=0.0,
                done=True,
                error=str(e).replace("\n", " "),
            )

    success = all(r >= SUCCESS_THRESHOLD for r in all_rewards)
    log_end(success=success, steps=total_steps, rewards=all_rewards)


if __name__ == "__main__":
    main()