"""
Scholarship data for ScholarAI.

The scholarships themselves live in `scholarships.json` (easy to edit, no Python needed).
For each scholarship you can set:
    "deadline": "2026-12-31"      a real date, OR leave it out and use
    "deadline_in_days": 30        a sample deadline counted from today
    "source_url": "https://..."   the official page
    "last_verified": "2026-10-04" the day YOU checked it on the official site
An entry with no last_verified date is shown as "sample data" in the app.
"""

import json
from datetime import date, timedelta
from pathlib import Path

TODAY = date.today()


def _load_scholarships():
    path = Path(__file__).parent / "scholarships.json"
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    for s in items:
        if not s.get("deadline"):
            s["deadline"] = (TODAY + timedelta(days=s.get("deadline_in_days", 30))).isoformat()
        s["verified"] = bool(s.get("last_verified"))
    return items


SCHOLARSHIPS = _load_scholarships()

# Master checklist = every document any scholarship asks for (so names always match).
DOCUMENT_CHECKLIST = sorted({doc for s in SCHOLARSHIPS for doc in s["docs"]})

CATEGORY_COLORS = {
    "Merit": "#4F46E5",
    "SC": "#0EA5E9",
    "ST": "#0891B2",
    "OBC": "#7C3AED",
    "EWS": "#DB2777",
    "Female": "#F59E0B",
    "PwD": "#16A34A",
    "Domicile": "#EA580C",
    "Minority": "#64748B",
}


GENDERS = ["Prefer not to say", "Female", "Male", "Other"]
STREAMS = ["STEM", "Commerce", "Arts", "Medical", "Other"]
STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal", "Delhi", "Jammu & Kashmir", "Ladakh", "Chandigarh",
    "Puducherry", "Other UT",
]
