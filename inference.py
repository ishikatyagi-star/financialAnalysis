import asyncio
import os
import json
import re
from typing import List, Optional
from openai import OpenAI

from financial_analysis_env.environment import FinancialAnalysisEnvironment
from financial_analysis_env.models import FinancialAnalysisAction


# ── CONFIG ─────────────────────────────────────────

IMAGE_NAME = os.getenv("IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

TASK_NAME = "financial_analysis"
BENCHMARK = "financial_analysis_env"

MAX_STEPS = 3
SUCCESS_THRESHOLD = 0.5


# ── LOGGING ────────────────────────────────────────

def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step, action, reward, done, error):
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── LLM CALL ───────────────────────────────────────

def get_model_response(client, task_description, financial_data):
    prompt = f"""
    You are a financial analyst.

    Task:
    {task_description}

    Data:
    {financial_data}

    Respond ONLY in JSON:
    {{
      "analysis": "...",
      "identified_issues": ["..."],
      "recommendation": "..."
    }}
    """

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )

        text = (completion.choices[0].message.content or "").strip()
    except Exception:
        text = ""

    def safe_parse(text):
        try:
            return json.loads(text)
        except Exception:
            # Try extracting JSON from messy output
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass

        return {
            "analysis": text,
            "identified_issues": [],
            "recommendation": text,
        }

    return safe_parse(text)


# ── MAIN ───────────────────────────────────────────

async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    env = FinancialAnalysisEnvironment()

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = env.reset()

        obs = result

        for step in range(1, MAX_STEPS + 1):
            action_dict = get_model_response(
                client,
                obs.task_description,
                obs.financial_data,
            )

            action = FinancialAnalysisAction(**action_dict)

            result = env.step(action)

            reward = result.reward or 0.0
            done = result.done

            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step,
                action=str(action_dict),
                reward=reward,
                done=done,
                error=None,
            )

            if done:
                break

        score = min(max(sum(rewards), 0.0), 1.0)
        success = score >= SUCCESS_THRESHOLD

    finally:
        env.close()
        log_end(success, steps_taken, score, rewards)


if __name__ == "__main__":
    asyncio.run(main())