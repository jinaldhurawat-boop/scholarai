"""
Scoring facade used by app.py.

    eligibility.py  - the honest, rule-based engine (decides eligibility)
    ml_model.py     - experimental selection-chance estimate (never decides eligibility)
"""

from __future__ import annotations

from eligibility import ELIGIBLE, ICON, evaluate
from ml_model import feature_importance, ml_score, model_report  # noqa: F401  (re-exported for app.py)


def rule_based_score(profile: dict, s: dict) -> int:
    """Ranking score 0-100. It is capped by the verdict, so it can never hide a failed rule."""
    return evaluate(profile, s)["score"]


def exact_match(profile: dict, s: dict) -> bool:
    return evaluate(profile, s)["verdict"] == ELIGIBLE


def score_reasons(profile: dict, s: dict) -> list[str]:
    """Rule-by-rule explanation, each line starts with ✅ / 🟡 / ❌."""
    return [f"{ICON[c['status']]} {c['text']}" for c in evaluate(profile, s)["checks"]]
