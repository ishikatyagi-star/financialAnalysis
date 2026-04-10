import re
import os
import random
from uuid import uuid4
from typing import Optional, Any, Tuple

try:
    from .models import FinancialAnalysisAction, FinancialAnalysisObservation
except ImportError:
    from models import FinancialAnalysisAction, FinancialAnalysisObservation


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _clamp(reward: float) -> float:
    return round(max(0.02, min(reward, 0.97)), 2)

def _whole_number(n: str, text: str) -> bool:
    return bool(re.search(r'(?<!\d)' + re.escape(n) + r'(?!\d)', text))

def _near(number: str, context_words: list, text: str, window: int = 80) -> float:
    m = re.search(r'(?<!\d)' + re.escape(number) + r'(?!\d)', text)
    if not m:
        return 0.0
    surrounding = text[max(0, m.start() - window): m.end() + window]
    return 1.0 if any(w in surrounding for w in context_words) else 0.4


# ── GRADERS — return (float, dict) for partial progress signals ───────────────

def grade_easy(action: FinancialAnalysisAction, expected: dict) -> Tuple[float, dict]:
    issues   = " ".join(i.lower() for i in action.identified_issues)
    analysis = action.analysis.lower()
    rec      = action.recommendation.lower()

    qualifier = ["best", "highest", "top", "strongest", "peak", "most"]
    fwd       = ["replicate", "sustain", "invest", "expand", "promote", "scale", "continue", "repeat"]

    # ── Deterministic success criteria (binary) ───────────────────────────────
    q2_correct     = ("q2" in issues and any(w in issues for w in qualifier)) or \
                     ("q2" in analysis and any(w in analysis for w in qualifier))
    growth_correct = bool(re.search(r'20\.8[0-9]?', analysis))
    rec_correct    = len(rec) > 40 and any(w in rec for w in fwd)

    # ── Partial scoring ───────────────────────────────────────────────────────
    quarter_score = 0.0
    if q2_correct:
        quarter_score = 0.35
    elif "q2" in issues or "q2" in analysis:
        quarter_score = 0.10  # found Q2 but no qualifier

    growth_score = 0.0
    if growth_correct:
        growth_score = 0.35
    elif re.search(r'20\.[5-9]', analysis):
        growth_score = 0.15
    elif "20%" in analysis or "21%" in analysis:
        growth_score = 0.06

    rec_score = 0.0
    if rec_correct and "q2" in rec:
        rec_score = 0.30
    elif rec_correct:
        rec_score = 0.15
    elif len(rec) > 20:
        rec_score = 0.05

    score = quarter_score + growth_score + rec_score

    return _clamp(score), {
        "criteria": {
            "q2_identified_as_best": q2_correct,
            "growth_pct_precise":    growth_correct,
            "recommendation_actionable": rec_correct,
        },
        "partial_scores": {
            "quarter":        round(quarter_score, 2),
            "growth":         round(growth_score, 2),
            "recommendation": round(rec_score, 2),
        },
        "success": q2_correct and growth_correct and rec_correct,
    }


def grade_medium(action: FinancialAnalysisAction, expected: dict) -> Tuple[float, dict]:
    issues   = " ".join(i.lower() for i in action.identified_issues)
    analysis = action.analysis.lower()
    rec      = action.recommendation.lower()

    anomaly_words   = ["spike", "anomaly", "unusual", "outlier", "jump", "surge", "deviation", "irregularity"]
    reasoning_words = ["compared to", "average", "baseline", "normal", "typical", "expected", "significantly"]
    specific_verbs  = [
        ("investigate", ["month 8", "310", "expense", "charge", "vendor", "cost"]),
        ("audit",       ["expense", "charge", "opex", "month 8"]),
        ("review",      ["month 8", "expense", "opex", "charge", "cost"]),
        ("escalate",    ["finance", "cfo", "management", "leadership"]),
        ("examine",     ["month 8", "expense", "charge", "310"]),
    ]

    # ── Deterministic success criteria (binary) ───────────────────────────────
    month_correct  = "month 8" in issues or "month 8" in analysis
    value_correct  = _whole_number("310", analysis)
    rec_specific   = any(
        verb in rec and any(ctx in rec for ctx in contexts)
        for verb, contexts in specific_verbs
    )

    # ── Partial scoring ───────────────────────────────────────────────────────
    id_score = 0.0
    if month_correct:
        magnitude   = value_correct
        has_compare = any(w in analysis for w in reasoning_words)
        if magnitude and has_compare:
            id_score = 0.35
        elif magnitude or has_compare:
            id_score = 0.25
        else:
            id_score = 0.15

    char_score = 0.0
    if any(w in analysis for w in anomaly_words) and any(w in analysis for w in reasoning_words):
        char_score = 0.30
    elif any(w in analysis for w in anomaly_words):
        char_score = 0.14

    rec_score_val = 0.0
    if rec_specific:
        rec_score_val = 0.25
    elif any(verb in rec for verb, _ in specific_verbs):
        rec_score_val = 0.08

    score = id_score + char_score + rec_score_val
    if len(action.identified_issues) == 0:
        score *= 0.4

    return _clamp(score), {
        "criteria": {
            "anomaly_month_correct": month_correct,   # only Month 8 is correct
            "anomaly_value_cited":   value_correct,   # 310 must appear
            "recommendation_specific": rec_specific,
        },
        "partial_scores": {
            "identification":    round(id_score, 2),
            "characterization":  round(char_score, 2),
            "recommendation":    round(rec_score_val, 2),
        },
        "success": month_correct and value_correct and rec_specific,
    }


def grade_hard(action: FinancialAnalysisAction, expected: dict) -> Tuple[float, dict]:
    issues      = [i.lower() for i in action.identified_issues]
    issues_text = " ".join(issues)
    analysis    = action.analysis.lower()
    rec         = action.recommendation.lower()

    RISK_KEYWORDS = {
        "margin": ["margin", "gross margin", "profitability"],
        "cac":    ["cac", "customer acquisition cost", "acquisition cost"],
        "opex":   ["opex", "operating expense", "operating cost"],
    }
    number_contexts = {
        "51":   ["margin", "gross", "q4", "percent", "%"],
        "198":  ["h1", "sales", "marketing", "spend", "cac"],
        "1380": ["h2", "revenue", "growth"],
        "4.7":  ["cac", "h1", "acquisition"],
        "7.9":  ["cac", "h2", "acquisition"],
    }
    rec_pairs = {
        "margin": [
            ("margin", ["improve", "recover", "protect", "increase", "optimize", "pricing", "raise"]),
            ("gross",  ["improve", "recover", "protect", "increase", "optimize"]),
        ],
        "cac": [
            ("cac",         ["reduce", "optimize", "improve", "lower", "cut", "efficiency"]),
            ("acquisition", ["reduce", "optimize", "efficiency", "cost"]),
        ],
        "opex": [
            ("opex",              ["control", "reduce", "freeze", "cut", "constrain", "limit"]),
            ("operating expense", ["control", "reduce", "freeze", "cut"]),
            ("headcount",         ["review", "freeze", "control", "justify", "limit"]),
        ],
    }
    causal_phrases = ["because", "due to", "driven by", "as a result",
                      "contributed to", "led to", "caused by", "resulting in", "attributed to"]

    # ── Deterministic success criteria (binary per risk) ──────────────────────
    risks_found = {
        risk: any(k in issues_text for k in kws)
        for risk, kws in RISK_KEYWORDS.items()
    }
    numbers_cited = {
        n: _near(n, number_contexts[n], analysis) > 0.5
        for n in expected["key_numbers"]
    }
    rec_addressed = {}
    for risk, pairs in rec_pairs.items():
        rec_addressed[risk] = any(
            domain in rec and any(v in rec for v in verbs)
            for domain, verbs in pairs
        )

    n_risks = sum(risks_found.values())
    if n_risks == 0:
        return _clamp(0.02), {
            "criteria": {"risks_identified": risks_found, "numbers_cited": numbers_cited, "rec_addressed": rec_addressed},
            "partial_scores": {"risk": 0.0, "numbers": 0.0, "recommendation": 0.0, "causal": 0.0, "bonus": 0.0},
            "success": False,
        }

    risk_score   = 0.28 * (n_risks / 3)
    num_score    = 0.28 * (sum(_near(n, number_contexts[n], analysis) for n in expected["key_numbers"]) / len(expected["key_numbers"]))
    rec_score    = 0.24 * (sum(rec_addressed.values()) / 3)
    causal_hits  = sum(1 for p in causal_phrases if p in analysis)
    causal_score = 0.12 * min(causal_hits / 2, 1.0)
    bonus_nums   = ["7.9", "4.7", "28", "35"]
    bonus_score  = 0.08 * min(sum(1 for n in bonus_nums if _whole_number(n, analysis)) / 2, 1.0)

    issue_penalty  = (len(issues) / 3) if len(issues) < 3 else 1.0
    length_penalty = (0.55 if len(action.analysis) < 80 else 1.0) * \
                     (0.65 if len(action.recommendation) < 60 else 1.0)

    total = (risk_score + num_score + rec_score + causal_score + bonus_score) * issue_penalty * length_penalty

    return _clamp(total), {
        "criteria": {
            "risks_identified": risks_found,        # dict — which of 3 risks found
            "numbers_cited":    numbers_cited,       # dict — which numbers cited in context
            "rec_addressed":    rec_addressed,       # dict — which risks addressed in rec
            "causal_reasoning": causal_hits >= 2,
        },
        "partial_scores": {
            "risk_identification":    round(risk_score, 2),
            "quantitative_support":   round(num_score, 2),
            "recommendation_quality": round(rec_score, 2),
            "reasoning_depth":        round(causal_score, 2),
            "bonus":                  round(bonus_score, 2),
        },
        "success": n_risks == 3 and all(numbers_cited.values()) and all(rec_addressed.values()),
    }


# ── TASK DEFINITIONS ──────────────────────────────────────────────────────────

TASKS = [
    {
        "difficulty": "easy",
        "task_description": (
            "You are a financial analyst. Below is quarterly revenue data for a retail company "
            "over the past year. Identify the best-performing quarter, calculate the growth "
            "percentage from Q1 to Q2, and provide a brief recommendation on how to sustain "
            "or build on that performance."
        ),
        "financial_data": {
            "company": "RetailCo", "period": "Annual", "currency": "USD (thousands)",
            "quarterly_revenue": {"Q1": 240, "Q2": 290, "Q3": 275, "Q4": 260},
            "notes": "Q2 included a successful summer promotion campaign.",
        },
        "expected": {"best_quarter": "Q2", "growth_pct": 20.8},
        "grader": lambda action, expected: grade_easy(action, expected),
    },
    {
        "difficulty": "medium",
        "task_description": (
            "You are a financial analyst reviewing monthly expense data for a SaaS company. "
            "One month shows a significant anomaly in operating expenses. Identify which month "
            "contains the anomaly, explain what makes it unusual, and recommend an appropriate "
            "next step for the finance team."
        ),
        "financial_data": {
            "company": "SaaSify Inc.", "period": "January – December", "currency": "USD (thousands)",
            "monthly_opex": {
                "Month 1": 120, "Month 2": 118, "Month 3": 125, "Month 4": 122,
                "Month 5": 119, "Month 6": 123, "Month 7": 121, "Month 8": 310,
                "Month 9": 124, "Month 10": 120, "Month 11": 126, "Month 12": 122,
            },
            "notes": "No major planned events or one-time charges were pre-disclosed for Month 8.",
        },
        "expected": {"anomaly_month": "Month 8"},
        "grader": lambda action, expected: grade_medium(action, expected),
    },
    {
        "difficulty": "hard",
        "task_description": (
            "You are a senior financial analyst conducting a comprehensive risk review for a "
            "B2B SaaS startup preparing for a Series B raise. Using the financial data below, "
            "identify the top three financial risks, support each risk with specific numbers "
            "from the data, and provide targeted recommendations. Consider margin trends, "
            "customer acquisition costs, and operating expense growth carefully."
        ),
        "financial_data": {
            "company": "GrowthLoop B2B", "period": "Last 12 months", "currency": "USD (thousands)",
            "revenue": {"H1": 1200, "H2": 1380},
            "gross_margin_pct": {"Q1": 68, "Q2": 63, "Q3": 58, "Q4": 51},
            "customer_acquisition": {
                "new_customers_H1": 42, "new_customers_H2": 39,
                "sales_marketing_spend_H1": 198, "sales_marketing_spend_H2": 310,
                "cac_H1": 4.7, "cac_H2": 7.9,
            },
            "operating_expenses": {"H1_total": 820, "H2_total": 1050, "yoy_opex_growth_pct": 28},
            "notes": "Company is pre-profitability. Headcount grew 35% in H2. No significant one-time charges recorded.",
        },
        "expected": {
            "top_risks": ["margin", "cac", "opex"],
            "key_numbers": ["51", "198", "1380"],
        },
        "grader": lambda action, expected: grade_hard(action, expected),
    },
]


# ── ENVIRONMENT CLASS ─────────────────────────────────────────────────────────

class FinancialAnalysisEnvironment:
    SUPPORTS_CONCURRENT_SESSIONS: bool = True
    metadata = {"render_modes": []}

    def __init__(self):
        self._current_task = None
        self._episode_id   = str(uuid4())
        self._step_count   = 0

    # Map of task IDs (matching openenv.yaml) → TASKS indices
    _TASK_ID_MAP = {"easy": 0, "medium": 1, "hard": 2}

    def reset(self, seed=None, task_id=None, episode_id=None, options=None) -> FinancialAnalysisObservation:
        if seed is not None:
            random.seed(seed)

        # Support episode_id from both the framework kwarg and legacy options dict
        if episode_id:
            self._episode_id = episode_id
        elif options and isinstance(options, dict):
            self._episode_id = options.get("episode_id", str(uuid4()))
        else:
            self._episode_id = str(uuid4())

        self._step_count = 0

        # Allow the checker/caller to select a specific task by ID
        if task_id is not None and task_id in self._TASK_ID_MAP:
            self._current_task = TASKS[self._TASK_ID_MAP[task_id]]
        elif options and isinstance(options, dict) and options.get("task_id") in self._TASK_ID_MAP:
            self._current_task = TASKS[self._TASK_ID_MAP[options["task_id"]]]
        else:
            self._current_task = random.choice(TASKS)

        return FinancialAnalysisObservation(
            task_description=self._current_task["task_description"],
            financial_data=self._current_task["financial_data"],
            difficulty=self._current_task["difficulty"],
            done=False,
            reward=None,       # No reward until step() is called
            reward_breakdown=None,
        )

    def step(self, action: FinancialAnalysisAction) -> FinancialAnalysisObservation:
        self._step_count += 1
        if self._current_task is None:
            self._current_task = random.choice(TASKS)

        reward, breakdown = self._current_task["grader"](action, self._current_task["expected"])

        return FinancialAnalysisObservation(
            task_description=self._current_task["task_description"],
            financial_data=self._current_task["financial_data"],
            difficulty=self._current_task["difficulty"],
            done=True,
            reward=reward,
            reward_breakdown=breakdown,
        )

    async def reset_async(self, seed=None, task_id=None, episode_id=None, options=None):
        return self.reset(seed=seed, task_id=task_id, episode_id=episode_id, options=options)

    async def step_async(self, action):
        return self.step(action)

    def close(self):
        self._current_task = None

    @property
    def state(self) -> dict:
        return {"episode_id": self._episode_id, "step_count": self._step_count}