# Financial Analysis Environment — Package

Core grading logic and Pydantic models for the `financial-analysis-env` OpenEnv submission.

## Contents

```
financial_analysis_env/
├── __init__.py     # Public exports: grade_easy/medium/hard/expert + models
├── environment.py  # Grading logic, TASKS registry, _clamp()
├── models.py       # FinancialAnalysisAction, FinancialAnalysisObservation
└── README.md       # This file
```

## Public API

```python
from financial_analysis_env import (
    grade_easy,
    grade_medium,
    grade_hard,
    grade_expert,
    FinancialAnalysisAction,
    FinancialAnalysisObservation,
)
```

### Action

```python
FinancialAnalysisAction(
    analysis="...",             # Detailed written analysis citing specific numbers
    identified_issues=["..."],  # List of anomalies or risk factors found
    recommendation="...",       # Specific, actionable business recommendation
)
```

### Observation

| Field | Type | Description |
|:------|:-----|:------------|
| `task_description` | `str` | The financial query the agent must answer |
| `financial_data` | `dict` | Raw numbers (quarterly/monthly/annual figures) |
| `difficulty` | `str` | `easy`, `medium`, `hard`, or `expert` |
| `done` | `bool` | `False` on reset; `True` after the single step |
| `reward` | `float \| None` | `None` on reset; strictly in `(0.01, 0.99)` after step |

### Graders

Each grader accepts a `FinancialAnalysisAction | None` and returns a `float` strictly in `(0.01, 0.99)`. Scores are clamped via `_clamp(epsilon=0.01)`.

| Function | Task | Criteria |
|:---------|:-----|:---------|
| `grade_easy` | Revenue Trend Analysis | Best quarter identified, QoQ growth % cited |
| `grade_medium` | Expense Anomaly Detection | Month 8 spike detected, audit recommendation given |
| `grade_hard` | Series B Risk Assessment | 3 risks identified with supporting numbers |
| `grade_expert` | Cash Runway & Covenant Audit | Runway calculated, covenant risk assessed, action proposed |

## Scoring Model

All graders use a **partial-credit weighted sum** across four components:

| Component | Weight | What it checks |
|:----------|:-------|:---------------|
| Issue identification | 30% | Correct anomaly / risk found in the right data field |
| Quantitative support | 30% | Key numbers cited with correct context |
| Recommendation quality | 20% | Actionable, specific, tied to the identified issue |
| Reasoning depth | 20% | Causal language linking data to business impact |

Scores are always clamped to `[0.01, 0.99]` — never exactly `0.0` or `1.0`.
