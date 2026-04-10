import re
import os
import random
from uuid import uuid4
from typing import Optional, Any

try:
    from .models import FinancialAnalysisAction, FinancialAnalysisObservation
except ImportError:
    from models import FinancialAnalysisAction, FinancialAnalysisObservation


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _clamp(reward: float) -> float:
    """Strictly (0, 1) — validator requires this."""
    return round(max(0.02, min(reward, 0.97)), 2)


def _whole_number(n: str, text: str) -> bool:
    """True if n appears as a standalone number in text (not inside 1380k, 510, etc.)"""
    return bool(re.search(r'(?<!\d)' + re.escape(n) + r'(?!\d)', text))


def _near(number: str, context_words: list, text: str, window: int = 80) -> float:
    """
    Returns 1.0 if number appears near a context word (within `window` chars).
    Returns 0.4 if number appears but without context.
    Returns 0.0 if number not found.
    """
    m = re.search(r'(?<!\d)' + re.escape(number) + r'(?!\d)', text)
    if not m:
        return 0.0
    surrounding = text[max(0, m.start() - window): m.end() + window]
    return 1.0 if any(w in surrounding for w in context_words) else 0.4


# ── GRADERS ───────────────────────────────────────────────────────────────────

def _easy_grader(action, expected):
    issues = " ".join(i.lower() for i in action.identified_issues)
    analysis = action.analysis.lower()
    rec = action.recommendation.lower()
    score = 0.0

    # 0.35 — correct quarter identified as best (must say best/highest near Q2)
    qualifier = ["best", "highest", "top", "strongest", "peak", "most"]
    if "q2" in issues and any(w in issues for w in qualifier):
        score += 0.35
    elif "q2" in analysis and any(w in analysis for w in qualifier):
        score += 0.22

    # 0.35 — growth % cited with precision (20.83% is correct)
    if re.search(r'20\.8[0-9]?', analysis):
        score += 0.35
    elif re.search(r'20\.[5-9]', analysis):
        score += 0.20
    elif "20%" in analysis or "21%" in analysis:
        score += 0.08

    # 0.30 — recommendation must mention Q2 + forward-looking action
    fwd = ["replicate", "sustain", "invest", "expand", "promote", "scale", "continue", "repeat"]
    if len(rec) > 60 and any(w in rec for w in fwd) and "q2" in rec:
        score += 0.30
    elif len(rec) > 40 and any(w in rec for w in fwd):
        score += 0.18
    elif len(rec) > 20:
        score += 0.07

    return _clamp(score)


def _medium_grader(action, expected):
    issues = " ".join(i.lower() for i in action.identified_issues)
    analysis = action.analysis.lower()
    rec = action.recommendation.lower()
    score = 0.0

    # 0.35 — Month 8 identified; bonus for quantifying magnitude
    if "month 8" in issues or "month 8" in analysis:
        magnitude = any(_whole_number(n, analysis) for n in ["310", "2.5", "150"])
        has_comparison = any(w in analysis for w in ["average", "baseline", "typical", "normal", "compared"])
        if magnitude and has_comparison:
            score += 0.35
        elif magnitude or has_comparison:
            score += 0.25
        else:
            score += 0.15  # identified but not quantified

    # 0.30 — anomaly characterised with reasoning, not just labeled
    anomaly_words  = ["spike", "anomaly", "unusual", "outlier", "jump", "surge", "deviation", "irregularity"]
    reasoning_words = ["compared to", "average", "baseline", "normal", "typical", "expected", "significantly"]
    if any(w in analysis for w in anomaly_words) and any(w in analysis for w in reasoning_words):
        score += 0.30
    elif any(w in analysis for w in anomaly_words):
        score += 0.14

    # 0.25 — specific recommendation (verb must be paired with context, not standalone)
    specific = [
        ("investigate", ["month 8", "310", "expense", "charge", "vendor", "cost"]),
        ("audit",       ["expense", "charge", "opex", "month 8"]),
        ("review",      ["month 8", "expense", "opex", "charge", "cost"]),
        ("escalate",    ["finance", "cfo", "management", "leadership"]),
        ("examine",     ["month 8", "expense", "charge", "310"]),
    ]
    for verb, contexts in specific:
        if verb in rec and any(ctx in rec for ctx in contexts):
            score += 0.25
            break
    else:
        if any(verb in rec for verb, _ in specific):
            score += 0.09  # verb present but no context

    if len(action.identified_issues) == 0:
        score *= 0.4

    return _clamp(score)


def _hard_grader(action, expected):
    issues = [i.lower() for i in action.identified_issues]
    issues_text = " ".join(issues)
    analysis = action.analysis.lower()
    rec = action.recommendation.lower()

    RISK_KEYWORDS = {
        "margin": ["margin", "gross margin", "profitability"],
        "cac":    ["cac", "customer acquisition cost", "acquisition cost"],
        "opex":   ["opex", "operating expense", "operating cost"],
    }

    # ── 1. Risk identification in issues list (0.28) ──────────────────────────
    risks_in_issues = sum(
        1 for kws in RISK_KEYWORDS.values()
        if any(k in issues_text for k in kws)
    )
    if risks_in_issues == 0:
        return _clamp(0.02)  # nothing identified — floor score
    risk_score = 0.28 * (risks_in_issues / 3)

    # ── 2. Key numbers cited with domain context (0.28) ───────────────────────
    number_contexts = {
        "51":   ["margin", "gross", "q4", "percent", "%"],
        "198":  ["h1", "sales", "marketing", "spend", "cac"],
        "1380": ["h2", "revenue", "growth"],
        "4.7":  ["cac", "h1", "acquisition"],
        "7.9":  ["cac", "h2", "acquisition"],
    }
    required = expected["key_numbers"]  # ["51", "198", "1380"]
    num_score = sum(
        _near(num, number_contexts[num], analysis)
        for num in required
    )
    num_score = 0.28 * (num_score / len(required))

    # ── 3. Recommendation — domain word + action verb pairs (0.24) ────────────
    rec_pairs = {
        "margin": [
            ("margin",  ["improve", "recover", "protect", "increase", "optimize", "pricing", "raise"]),
            ("gross",   ["improve", "recover", "protect", "increase", "optimize"]),
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
    rec_hits = 0
    for risk, pairs in rec_pairs.items():
        for domain, verbs in pairs:
            if domain in rec and any(v in rec for v in verbs):
                rec_hits += 1
                break
    rec_score = 0.24 * (rec_hits / 3)

    # ── 4. Causal reasoning depth (0.12) ──────────────────────────────────────
    causal = ["because", "due to", "driven by", "as a result",
              "contributed to", "led to", "caused by", "resulting in", "attributed to"]
    causal_hits = sum(1 for p in causal if p in analysis)
    causal_score = 0.12 * min(causal_hits / 2, 1.0)  # needs 2+ to max out

    # ── 5. Bonus: extra numbers cited (0.08) ──────────────────────────────────
    bonus_nums = ["7.9", "4.7", "28", "35"]
    bonus_hits = sum(1 for n in bonus_nums if _whole_number(n, analysis))
    bonus_score = 0.08 * min(bonus_hits / 2, 1.0)

    # ── Penalties ─────────────────────────────────────────────────────────────
    issue_penalty  = (len(issues) / 3) if len(issues) < 3 else 1.0
    length_penalty = 1.0
    if len(action.analysis) < 80:
        length_penalty *= 0.55
    if len(action.recommendation) < 60:
        length_penalty *= 0.65

    total = (risk_score + num_score + rec_score + causal_score + bonus_score)
    total *= issue_penalty * length_penalty

    return _clamp(total)


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
            "company": "RetailCo",
            "period": "Annual",
            "currency": "USD (thousands)",
            "quarterly_revenue": {"Q1": 240, "Q2": 290, "Q3": 275, "Q4": 260},
            "notes": "Q2 included a successful summer promotion campaign.",
        },
        "expected": {"best_quarter": "Q2", "growth_pct": 20.8},
        "grader": lambda action, expected: _easy_grader(action, expected),
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
            "company": "SaaSify Inc.",
            "period": "January – December",
            "currency": "USD (thousands)",
            "monthly_opex": {
                "Month 1": 120, "Month 2": 118, "Month 3": 125,
                "Month 4": 122, "Month 5": 119, "Month 6": 123,
                "Month 7": 121, "Month 8": 310, "Month 9": 124,
                "Month 10": 120, "Month 11": 126, "Month 12": 122,
            },
            "notes": "No major planned events or one-time charges were pre-disclosed for Month 8.",
        },
        "expected": {"anomaly_month": "Month 8"},
        "grader": lambda action, expected: _medium_grader(action, expected),
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
            "company": "GrowthLoop B2B",
            "period": "Last 12 months",
            "currency": "USD (thousands)",
            "revenue": {"H1": 1200, "H2": 1380},
            "gross_margin_pct": {"Q1": 68, "Q2": 63, "Q3": 58, "Q4": 51},
            "customer_acquisition": {
                "new_customers_H1": 42,          "new_customers_H2": 39,
                "sales_marketing_spend_H1": 198, "sales_marketing_spend_H2": 310,
                "cac_H1": 4.7,                   "cac_H2": 7.9,
            },
            "operating_expenses": {
                "H1_total": 820, "H2_total": 1050, "yoy_opex_growth_pct": 28,
            },
            "notes": (
                "Company is pre-profitability. Headcount grew 35% in H2. "
                "No significant one-time charges recorded."
            ),
        },
        "expected": {
            "top_risks": ["margin", "cac", "opex"],
            "key_numbers": ["51", "198", "1380"],
        },
        "grader": lambda action, expected: _hard_grader(action, expected),
    },
]


# ── GLOBAL STATE ──────────────────────────────────────────────────────────────

_current_task  = None
_current_state = {"episode_id": str(uuid4()), "step_count": 0}


# ── ENVIRONMENT CLASS (unchanged) ─────────────────────────────────────────────

class FinancialAnalysisEnvironment:
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    async def reset_async(self, seed=None, options=None):
        return self.reset(seed=seed, options=options)

    async def step_async(self, action):
        return self.step(action)

    def seed(self, seed=None):
        random.seed(seed)

    metadata = {"render_modes": []}

    def reset(self, seed=None, options=None) -> FinancialAnalysisObservation:
        global _current_task, _current_state
        if seed is not None:
            random.seed(seed)

        _current_state = {
            "episode_id": options.get("episode_id", str(uuid4())) if options else str(uuid4()),
            "step_count": 0,
        }
        _current_task = random.choice(TASKS)

        return FinancialAnalysisObservation(
            task_description=_current_task["task_description"],
            financial_data=_current_task["financial_data"],
            difficulty=_current_task["difficulty"],
            done=False,
            reward=0.0,
        )

    def step(self, action: FinancialAnalysisAction) -> FinancialAnalysisObservation:
        global _current_task, _current_state
        _current_state["step_count"] += 1

        if _current_task is None:
            _current_task = random.choice(TASKS)

        reward = _current_task["grader"](action, _current_task["expected"])

        return FinancialAnalysisObservation(
            task_description=_current_task["task_description"],
            financial_data=_current_task["financial_data"],
            difficulty=_current_task["difficulty"],
            done=True,
            reward=reward,
        )

    def _calculate_reward(self, action: FinancialAnalysisAction) -> float:
        return _current_task["grader"](action, _current_task["expected"])

    def close(self):
        pass

    @property
    def state(self) -> dict:
        return _current_state