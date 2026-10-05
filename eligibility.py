"""
The eligibility engine (pure Python: no Streamlit, no ML, easy to test).

Idea in one line:  a scholarship has MUST-PASS rules. If a hard rule fails,
the student is NOT eligible, no matter how good the other numbers are.

Verdicts
    eligible      -> every rule passes
    borderline    -> nothing hard fails, but income / marks are only slightly off
    not_eligible  -> at least one rule clearly fails (e.g. wrong category)

The 0-100 `score` is only used to RANK scholarships inside a verdict.
It can never lift a student into a better verdict.
"""

from __future__ import annotations

INCOME_TOLERANCE = 1.10   # up to 10% over the income limit = "borderline"
MARKS_TOLERANCE = 3       # up to 3 points under the marks minimum = "borderline"

ELIGIBLE, BORDERLINE, NOT_ELIGIBLE = "eligible", "borderline", "not_eligible"
VERDICT_ORDER = {ELIGIBLE: 0, BORDERLINE: 1, NOT_ELIGIBLE: 2}   # lower = better
VERDICT_LABEL = {
    ELIGIBLE: ("✅ Eligible", "good"),
    BORDERLINE: ("🟡 Borderline", "warn"),
    NOT_ELIGIBLE: ("❌ Not eligible", "bad"),
}

PASS, NEAR, FAIL = "pass", "near", "fail"
ICON = {PASS: "✅", NEAR: "🟡", FAIL: "❌"}

# What each special group needs, in plain words.
GROUP_NEEDS = {
    "Domicile": "Needs Maharashtra domicile",
    "Female": "Open to female applicants only",
    "PwD": "Needs a certified disability",
    "Minority": "Needs minority-community status",
}


def group_matches(profile: dict, s: dict) -> bool:
    """Hard rule: does the student belong to the group this scholarship is for?"""
    cat = s["category"]
    if cat == "Merit":
        return True
    if cat == "Domicile":
        return bool(profile.get("domicile"))
    if cat == "Female":
        return bool(profile.get("female"))
    if cat == "PwD":
        return bool(profile.get("disability"))
    if cat == "Minority":
        return bool(profile.get("minority"))
    return cat == profile.get("category")        # SC / ST / OBC / EWS


def _income_check(profile: dict, s: dict) -> dict:
    income, limit = profile["income"], s["income_limit"]
    if income <= limit:
        return {"rule": "Income", "status": PASS,
                "text": f"Family income ₹{income:,} is within the ₹{limit:,} limit."}
    if income <= limit * INCOME_TOLERANCE:
        over = income - limit
        return {"rule": "Income", "status": NEAR,
                "text": f"Income is ₹{over:,} over the ₹{limit:,} limit. Close, check if a relaxation applies."}
    return {"rule": "Income", "status": FAIL,
            "text": f"Income ₹{income:,} is above the ₹{limit:,} limit."}


def _marks_check(profile: dict, s: dict) -> dict:
    marks, need = profile["academic"], s["min_academic"]
    if marks >= need:
        return {"rule": "Marks", "status": PASS,
                "text": f"Academic score {marks:g} meets the {need}+ requirement."}
    if marks >= need - MARKS_TOLERANCE:
        return {"rule": "Marks", "status": NEAR,
                "text": f"Academic score {marks:g} is {need - marks:g} short of the {need} minimum."}
    return {"rule": "Marks", "status": FAIL,
            "text": f"Academic score {marks:g} is below the {need} minimum."}


def _group_check(profile: dict, s: dict) -> dict:
    cat = s["category"]
    if group_matches(profile, s):
        text = "Open to all categories." if cat == "Merit" else f"You belong to the group this is for ({cat})."
        return {"rule": "Group", "status": PASS, "text": text}
    need = GROUP_NEEDS.get(cat, f"Only for {cat} category students")
    return {"rule": "Group", "status": FAIL, "text": f"{need}."}


def _requirement_checks(profile: dict, s: dict) -> list[dict]:
    """Extra must-pass rules, read from the scholarship's optional "requires" dictionary."""
    req = s.get("requires", {})
    checks = []
    if "stream" in req:
        ok = profile.get("stream") == req["stream"]
        text = (f"Your field of study ({req['stream']}) matches." if ok
                else f"Needs a {req['stream']} course of study.")
        checks.append({"rule": "Field of study", "status": PASS if ok else FAIL, "text": text})
    if "state" in req:
        ok = profile.get("state") == req["state"]
        text = (f"You are from {req['state']}." if ok else f"Only for students from {req['state']}.")
        checks.append({"rule": "State", "status": PASS if ok else FAIL, "text": text})
    if req.get("first_gen"):
        ok = bool(profile.get("first_gen"))
        text = ("You are the first in your family to attend college." if ok
                else "Only for first-generation college students.")
        checks.append({"rule": "First generation", "status": PASS if ok else FAIL, "text": text})
    return checks


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def evaluate(profile: dict, s: dict) -> dict:
    """Return {verdict, checks, score} for one student and one scholarship."""
    checks = [_income_check(profile, s), _marks_check(profile, s), _group_check(profile, s)]
    checks += _requirement_checks(profile, s)
    statuses = [c["status"] for c in checks]

    if FAIL in statuses:
        verdict = NOT_ELIGIBLE
        # 0, 10 or 20 depending on how many rules still pass
        score = round(30 * statuses.count(PASS) / len(checks))
    elif NEAR in statuses:
        verdict = BORDERLINE
        score = 50 + 5 * statuses.count(PASS)            # 50-60, always below eligible
    else:
        verdict = ELIGIBLE
        income_room = _clamp((s["income_limit"] - profile["income"]) / s["income_limit"])
        marks_room = _clamp((profile["academic"] - s["min_academic"]) / max(1, 100 - s["min_academic"]))
        score = round(70 + 30 * (0.5 * income_room + 0.5 * marks_room))   # 70-100

    return {"verdict": verdict, "checks": checks, "score": score}


def smallest_change(profile: dict, s: dict):
    """What would have to change to qualify?  (used by the What-if page)

    Returns a list of plain-English steps ([] if already eligible),
    or None when the gap is something sliders can't fix (category, gender, ...).
    """
    ev = evaluate(profile, s)
    if ev["verdict"] == ELIGIBLE:
        return []
    steps = []
    for c in ev["checks"]:
        if c["status"] == PASS:
            continue
        if c["rule"] == "Income":
            steps.append(f"Income would need to be at most ₹{s['income_limit']:,} (now ₹{profile['income']:,}).")
        elif c["rule"] == "Marks":
            gap = s["min_academic"] - profile["academic"]
            steps.append(f"Marks would need to reach {s['min_academic']} (now {profile['academic']:g}, so +{gap:g}).")
        else:
            return None
    return steps
