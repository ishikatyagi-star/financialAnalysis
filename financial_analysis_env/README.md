---
title: Financial Analysis Env Environment Server
emoji: 📊
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
base_path: /web
tags:
  - openenv
---

# Financial Analysis Environment

## Motivation

Financial analysis is a high-stakes, real-world task that requires reasoning over structured numeric data, identifying patterns, and producing actionable insights. This environment trains AI agents to perform the kind of analysis a junior financial analyst would do — given raw financial data, the agent must identify what matters, support it with numbers, and recommend a course of action.

This directly maps to real products (automated financial reporting, CFO dashboards, investment screening tools) and provides a clean, verifiable reward signal with natural partial credit.

---

## Environment Description

The agent receives a financial dataset and must produce a structured analysis. Tasks range from simple trend identification to comprehensive risk assessments. Each task has a programmatic grader that scores the response strictly between 0 and 1, rewarding:
- Correct identification of the key finding
- Quantitative support (citing specific numbers from the data)
- Quality and specificity of recommendations
- Causal reasoning depth

---

## Action Space

The agent submits a `FinancialAnalysisAction` with three fields:

| Field | Type | Description |
|---|---|---|
| `identified_issues` | `List[str]` | List of issues/findings identified in the data. Minimum 3 for hard tasks. |
| `analysis` | `str` | Detailed analysis supporting the identified issues with numbers from the data |
| `recommendation` | `str` | Specific, actionable recommendations addressing the findings |

```python
FinancialAnalysisAction(
    identified_issues=[
        "Q2 was the best performing quarter with revenue of 290k",
        "Q1 to Q2 growth was 20.8%",
        "Q3 and Q4 show declining momentum"
    ],
    analysis="Q2 achieved peak revenue of 290k, representing 20.8% growth from Q1's 240k, driven by the summer promotion campaign. Q3 and Q4 declined to 275k and 260k respectively.",
    recommendation="Sustain Q2 momentum by replicating the summer promotion campaign annually and expanding it to Q3 to reduce the seasonal drop-off."
)
```

---

## Observation Space

The environment returns a `FinancialAnalysisObservation` after each `reset()` and `step()`:

| Field | Type | Description |
|---|---|---|
| `task_description` | `str` | Full description of the task the agent must complete |
| `financial_data` | `dict` | Structured financial data (revenue, expenses, ratios, etc.) |
| `difficulty` | `str` | Task difficulty: `"easy"`, `"medium"`, or `"hard"` |
| `done` | `bool` | `False` after reset, `True` after step (single-turn environment) |
| `reward` | `float` | Score strictly in `(0, 1)` — only set after `step()` |

---

## Tasks

### Task 0 — Easy: Quarterly Revenue Analysis

**Objective**: Given quarterly revenue data for a retail company, identify the best-performing quarter, calculate the precise growth percentage from Q1 to Q2, and recommend how to sustain that performance.

**Data provided**: 4 quarters of revenue figures + contextual notes

**Grader criteria**:
| Criterion | Weight | What earns it |
|---|---|---|
| Correct quarter identified | 0.35 | "Q2" labeled as best/highest/peak in issues or analysis |
| Precise growth % cited | 0.35 | "20.8%" or "20.83%" in analysis (not just "~20%") |
| Actionable recommendation | 0.30 | Forward-looking verb (sustain/replicate/expand) + Q2 reference |

**Baseline score**: `0.07` (dummy action) → `~0.88` (correct answer)

---

### Task 1 — Medium: Expense Anomaly Detection

**Objective**: Given 12 months of operating expense data for a SaaS company, identify which month contains an anomaly, explain what makes it unusual with quantitative comparison, and recommend a specific next step for the finance team.

**Data provided**: Monthly opex figures across 12 months (one month has a 2.5x spike)

**Grader criteria**:
| Criterion | Weight | What earns it |
|---|---|---|
| Correct month identified | 0.35 | "Month 8" in issues or analysis + magnitude/comparison |
| Anomaly characterised | 0.30 | Anomaly word (spike/outlier/deviation) + reasoning word (average/baseline/compared) |
| Specific recommendation | 0.25 | Action verb (investigate/audit/review) paired with context (month 8/310/expense) |

**Baseline score**: `0.09` (dummy action) → `~0.89` (correct answer)

---

### Task 2 — Hard: Series B Risk Assessment

**Objective**: Given 12 months of financial data for a B2B SaaS startup preparing for a Series B raise, identify the top 3 financial risks, support each with specific numbers from the data, and provide targeted recommendations for each risk.

**Data provided**: Revenue (H1/H2), gross margin by quarter, CAC and S&M spend (H1/H2), opex figures, headcount notes

**Grader criteria**:
| Criterion | Weight | What earns it |
|---|---|---|
| All 3 risks identified in issues | 0.28 | Margin + CAC + OpEx each present in `identified_issues` |
| Key numbers cited with context | 0.28 | "51", "198", "1380" each appearing near relevant domain words |
| Targeted recommendations | 0.24 | Domain word + action verb pairs per risk (e.g. "cac" + "reduce") |
| Causal reasoning | 0.12 | 2+ causal phrases ("due to", "driven by", "as a result", etc.) |
| Bonus numbers | 0.08 | Additional data points cited (7.9, 4.7, 28, 35) |

**Baseline score**: `0.02` (dummy action) → `~0.92` (correct answer)

---

## Reward Function

All graders return a float **strictly between 0 and 1** (clamped to `[0.02, 0.97]`).

Rewards provide **partial progress signals** — the agent is not penalized for partial answers, but must demonstrate increasing quality to unlock higher scores:

```
0.02 – 0.20  : Wrong or missing key finding
0.20 – 0.50  : Correct finding, weak support
0.50 – 0.75  : Correct finding, partial quantitative support
0.75 – 0.97  : Correct finding, strong numbers, specific recommendations
```

---

## Setup & Usage

### Local Development

```bash
git clone https://github.com/YOUR_USERNAME/mutantsSubmission
cd mutantsSubmission
pip install -r requirements.txt
uvicorn server.app:app --reload --port 7860
```

### Docker

```bash
docker build -t financial-analysis-env .
docker run -p 7860:7860 financial-analysis-env
```

### Python Client

```python
from financial_analysis_env import FinancialAnalysisAction, FinancialAnalysisEnv

with FinancialAnalysisEnv(base_url="https://YOUR_SPACE.hf.space") as env:
    obs = env.reset()
    print(obs.observation.task_description)
    print(obs.observation.difficulty)

    result = env.step(FinancialAnalysisAction(
        identified_issues=[
            "Q2 was the best performing quarter with revenue of 290k",
            "Growth from Q1 to Q2 was 20.8%"
        ],
        analysis="Q2 revenue reached 290k, a 20.8% increase from Q1's 240k, driven by the summer promotion campaign.",
        recommendation="Sustain Q2 momentum by replicating the summer promotion and expanding it into Q3."
    ))
    print(f"Reward: {result.reward}")
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `API_BASE_URL` | LLM API endpoint | `https://api.openai.com/v1` |
| `MODEL_NAME` | Model identifier | `gpt-4.1-mini` |
| `HF_TOKEN` | Hugging Face / API key | Required |

---

## Baseline Scores

Scores from running `inference.py` with `gpt-4.1-mini` on each task:

| Task | Difficulty | Baseline Score |
|---|---|---|
| Quarterly Revenue Analysis | Easy | 0.07 (dummy) |
| Expense Anomaly Detection | Medium | 0.09 (dummy) |
| Series B Risk Assessment | Hard | 0.02 (dummy) |

Run `/run_test` on the deployed Space to verify all graders are working.

---

## Endpoints

| Endpoint | Description |
|---|---|
| `/web` | Interactive web UI |
| `/docs` | OpenAPI / Swagger docs |
| `/health` | Health check |
| `/tasks` | List all 3 tasks with grader metadata |
| `/run_test` | Run all 3 graders and verify reward range |

---

## Project Structure

```
mutantsSubmission/
├── financial_analysis_env/
│   ├── __init__.py
│   ├── environment.py          # Core environment + 3 graders (easy/medium/hard)
│   ├── models.py               # FinancialAnalysisAction + FinancialAnalysisObservation
│   └── README.md               # This file
├── server/
│   ├── __init__.py
│   └── app.py                  # FastAPI app (reset/step/state + /tasks /health /run_test)
├── inference.py                # Agent script — LLM calls + [START]/[STEP]/[END] logs
├── openenv.yaml                # OpenEnv manifest
├── Dockerfile                  # Container definition
├── pyproject.toml              # Project metadata and dependencies
├── requirements.txt            # Python dependencies
└── uv.lock                     # Locked dependencies
```
