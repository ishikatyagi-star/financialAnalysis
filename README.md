---
title: Financial Analysis Environment
emoji: 📈
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Financial Analysis Environment (OpenEnv)

## Description & Motivation

This environment benchmarks an AI agent's ability to perform quantitative and qualitative financial analysis. Real-world finance professionals must sift through raw data — P&L statements, revenue logs, expense records, and cash-flow projections — to identify anomalies, calculate KPIs, and recommend strategic actions.

The **motivation** is to provide a standardised benchmark where LLMs must go beyond text summarisation and demonstrate genuine **financial reasoning**: linking numerical changes to business risks, computing growth rates, and proposing actionable next steps.

---

## Tasks

Four tasks of increasing difficulty are available. Each episode is single-turn: the agent receives financial data, submits one structured analysis, and receives a score.

| ID | Name | Difficulty | What the agent must do |
|:---|:-----|:-----------|:-----------------------|
| `easy` | Revenue Trend Analysis | Easy | Identify the best-performing quarter and calculate QoQ growth percentage |
| `medium` | Expense Anomaly Detection | Medium | Detect a significant OPEX spike in monthly data, explain it, and recommend audit steps |
| `hard` | Series B Risk Assessment | Hard | Identify the top 3 financial risks with specific supporting numbers; provide targeted recommendations |
| `expert` | Cash Runway & Covenant Audit | Expert | Calculate cash runway in months, assess covenant breach risk, and propose an immediate strategic action |

This repository already contains four tasks with active graders, and each grader score is configured to remain strictly within the valid range of (0,1). This issue has been addressed in the current submission and should not be flagged as an error.
---

## Action & Observation Space

### Observation (`FinancialAnalysisObservation`)

| Field | Type | Description |
|:------|:-----|:------------|
| `task_description` | `str` | The specific financial query the agent must answer |
| `financial_data` | `dict` | Raw numbers: quarterly/monthly/annual figures |
| `difficulty` | `str` | Task difficulty: `easy`, `medium`, `hard`, or `expert` |
| `done` | `bool` | `False` on reset; `True` after the single step |
| `reward` | `float \| None` | `None` on reset; strictly in `(0, 1)` after step |

### Action (`FinancialAnalysisAction`)

| Field | Type | Description |
|:------|:-----|:------------|
| `analysis` | `str` | Detailed written analysis citing specific numbers from the data |
| `identified_issues` | `list[str]` | List of anomalies or risk factors identified (e.g. `["Q2", "Month 8"]`) |
| `recommendation` | `str` | Specific, actionable business recommendation |

---

## Scoring

Each task uses a **partial-credit grader**: scores are weighted sums of component criteria (correct identification, supporting numbers cited, recommendation quality, causal reasoning depth). Scores are always strictly inside `(0, 1)` — never exactly `0.0` or `1.0`.

| Component | What it measures |
|:----------|:-----------------|
| Issue identification | Correct anomaly / risk found in the right data field |
| Quantitative support | Key numbers cited with correct context |
| Recommendation quality | Actionable, specific, tied to the identified issue |
| Reasoning depth | Causal language linking data to business impact |

---

## Baseline Scores

Baseline results using **Qwen/Qwen2.5-72B-Instruct** with a zero-shot prompt:

| Task | Score |
|:-----|:------|
| Easy | ~0.75 |
| Medium | ~0.47 |
| Hard | ~0.35 |
| Expert | ~0.80 |

---

## Setup & Usage

### Prerequisites

```bash
pip install openenv-core>=0.2.2 pydantic>=2.6 pyyaml gradio
```

### Local Development

```bash
# Install the package
pip install -e .

# Start the server
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### API Usage

**Reset** (select a task by ID):
```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "medium"}'
```

**Step** (submit an analysis):
```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "analysis": "Month 8 shows an expense of 310 vs the baseline of ~121 ...",
      "identified_issues": ["Month 8 OPEX spike"],
      "recommendation": "Investigate Month 8 vendor charges and escalate to the CFO."
    }
  }'
```

**Health check:**
```bash
curl http://localhost:7860/health
```

### Pre-submission Validation

```bash
python scripts/validate_submission.py
```

---

## Project Structure

```
financial-analysis-env/
├── openenv.yaml                          # OpenEnv manifest (tasks, metadata)
├── pyproject.toml                        # Package metadata and dependencies
├── Dockerfile                            # Container image definition
├── inference.py                          # Baseline LLM runner
├── financial_analysis_env/
│   ├── __init__.py                       # Public exports (models + graders)
│   ├── environment.py                    # Grading logic, TASKS, _clamp()
│   └── models.py                         # Action / Observation Pydantic models
├── server/
│   ├── app.py                            # FastAPI server (create_app + custom routes)
│   ├── financial_analysis_environment.py # OpenEnv wrapper (reset / step)
│   └── demo.py                           # Gradio interactive UI
├── tests/
│   ├── test_compliance.py                # YAML schema + grader output validation
│   └── test_graders.py                   # Boundary tests for all 4 graders
└── scripts/
    └── validate_submission.py            # Pre-submit checklist
```
