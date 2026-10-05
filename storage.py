"""
Tiny local JSON persistence layer.

Streamlit's `st.session_state` already keeps data alive for the length of a
browser session, but it resets whenever the server restarts. Writing to a
small JSON file next to the app lets a single-user local run (e.g. a college
demo on one laptop) remember a profile, saved scholarships and the document
checklist across restarts — without needing a database.

This is best-effort: any read/write failure is swallowed so the app never
crashes because of it, it just falls back to an empty state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "user_data.json"


def load_user_data() -> dict[str, Any]:
    try:
        if DATA_FILE.exists():
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_user_data(data: dict[str, Any]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass
