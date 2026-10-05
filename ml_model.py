"""
Experimental "chance of being selected" model.

HONEST SUMMARY (this is also shown on the Scoring page):
  * Eligibility is decided by the rules in eligibility.py, never by this model.
  * This model only estimates a rough chance of being SELECTED once a student
    is eligible (many scholarships have far fewer awards than applicants).
  * There is no real application history available, so it is trained on
    SYNTHETIC data generated below. High accuracy therefore only proves that the
    model learned our own assumptions, not that it predicts real outcomes.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from eligibility import BORDERLINE, ELIGIBLE, FAIL, NEAR, NOT_ELIGIBLE, evaluate

FEATURE_NAMES = ["Income vs limit", "Marks above minimum", "Rules clearly failed", "Rules nearly missed"]


def features(profile: dict, s: dict) -> list[float]:
    """Same 4 numbers for every scholarship, so one model can serve all of them."""
    statuses = [c["status"] for c in evaluate(profile, s)["checks"]]
    income_ratio = min(profile["income"] / s["income_limit"], 3.0)
    marks_gap = max(-30.0, min(50.0, profile["academic"] - s["min_academic"]))
    return [income_ratio, marks_gap, float(statuses.count(FAIL)), float(statuses.count(NEAR))]


def make_synthetic_data(n: int = 2500, seed: int = 42):
    """Pretend history. ASSUMPTIONS (ours, not real data):
       - a student who clearly fails a rule is never selected
       - otherwise a better marks margin and lower income raise the chance
       - each nearly-missed rule lowers it
    """
    rng = np.random.default_rng(seed)
    income_ratio = rng.uniform(0.0, 1.6, n)
    marks_gap = rng.uniform(-15.0, 45.0, n)
    fails = rng.choice([0, 1, 2], size=n, p=[0.5, 0.35, 0.15])
    near = rng.choice([0, 1, 2], size=n, p=[0.7, 0.2, 0.1])
    z = -0.8 + 0.06 * marks_gap + 1.8 * (1 - np.minimum(income_ratio, 1.2)) - 1.0 * near
    p = 1 / (1 + np.exp(-z))
    y = (rng.random(n) < p).astype(int)
    y[fails > 0] = 0
    X = np.column_stack([income_ratio, marks_gap, fails, near])
    return X, y


@lru_cache(maxsize=1)
def get_model():
    """Train once. Returns (model, report) where report holds honest test-set metrics."""
    X, y = make_synthetic_data()
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=0, stratify=y)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    model.fit(X_tr, y_tr)
    proba = model.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    report = {
        "n_train": int(len(y_tr)),
        "n_test": int(len(y_te)),
        "positive_rate": float(y.mean()),
        "accuracy": float(accuracy_score(y_te, pred)),
        "baseline": float(max(y_te.mean(), 1 - y_te.mean())),
        "auc": float(roc_auc_score(y_te, proba)),
        "brier": float(brier_score_loss(y_te, proba)),
        "confusion": confusion_matrix(y_te, pred).tolist(),
    }
    return model, report


def model_report() -> dict:
    return get_model()[1]


def ml_score(profile: dict, s: dict) -> int:
    """Rough chance (0-100) of selection. The rule verdict always wins: a clear fail stays tiny."""
    model, _ = get_model()
    raw = round(float(model.predict_proba(np.array([features(profile, s)]))[0][1]) * 100)
    verdict = evaluate(profile, s)["verdict"]
    cap = {ELIGIBLE: 100, BORDERLINE: 60, NOT_ELIGIBLE: 10}[verdict]
    return min(raw, cap)


def feature_importance() -> list[tuple[str, float]]:
    """Coefficients on standardised features, so the sizes are comparable."""
    model, _ = get_model()
    coefs = model.named_steps["logisticregression"].coef_[0]
    return list(zip(FEATURE_NAMES, [float(c) for c in coefs]))