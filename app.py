from __future__ import annotations

import html
import io
import json
import hashlib
from pathlib import Path
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="ScholarAI | Smart Scholarship Finder", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# ================= AUTHENTICATION SYSTEM =================
# Demo/local authentication for the Streamlit project.
# Accounts are stored locally in auth_users.json next to this app.py.
AUTH_FILE = Path(__file__).with_name("auth_users.json")

def _hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _load_auth_users():
    if not AUTH_FILE.exists():
        return {}
    try:
        with AUTH_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}

def _save_auth_users(users):
    with AUTH_FILE.open("w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def _valid_username(username):
    return username and username.strip().replace("_", "").isalnum() and 3 <= len(username.strip()) <= 30

def _valid_email(email):
    email = email.strip()
    return "@" in email and "." in email.split("@")[-1] and " " not in email

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

def _show_auth_page():
    st.markdown("""
    <style>
    .auth-wrap { max-width: 560px; margin: 5vh auto 0 auto; }
    .auth-card { padding: 2rem 2.2rem; border: 1px solid #e7e9f0; border-radius: 22px; background: white; box-shadow: 0 12px 35px rgba(30,35,60,.08); }
    .auth-logo { width: 64px; height: 64px; border-radius: 18px; display:flex; align-items:center; justify-content:center; background: #f0efff; color:#635bff; font-size: 32px; margin-bottom: 14px; }
    .auth-sub { color:#777d8f; margin-bottom: 1.2rem; }
    </style>
    <div class="auth-wrap">
      <div class="auth-card">
        <div class="auth-logo">🎓</div>
        <h1 style="margin:0;">ScholarAI</h1>
        <p class="auth-sub">Smart Scholarship Eligibility Predictor</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    login_tab, signup_tab, forgot_tab = st.tabs(["🔐 Login", "📝 Sign Up", "🔑 Forgot Password"])
    users = _load_auth_users()

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            submitted = st.form_submit_button("Login", type="primary", width="stretch")

        if submitted:
            username_key = username.strip().lower()
            record = users.get(username_key)
            if record and record.get("password") == _hash_password(password):
                st.session_state.logged_in = True
                st.session_state.auth_user = username_key
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("Username", placeholder="Choose a username", key="signup_username")
            new_email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
            new_password = st.text_input("Password", type="password", placeholder="Minimum 6 characters", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password", key="signup_confirm")
            registered = st.form_submit_button("Create Account", type="primary", width="stretch")

        if registered:
            username_key = new_username.strip().lower()
            email_key = new_email.strip().lower()

            if not _valid_username(username_key):
                st.error("Username must be 3–30 characters and contain only letters, numbers, or underscores.")
            elif username_key in users:
                st.error("This username is already registered. Please choose another one.")
            elif not _valid_email(email_key):
                st.error("Please enter a valid email address.")
            elif any(str(v.get("email", "")).lower() == email_key for v in users.values()):
                st.error("This email is already registered.")
            elif len(new_password) < 6:
                st.error("Password must contain at least 6 characters.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                users[username_key] = {
                    "email": email_key,
                    "password": _hash_password(new_password),
                }
                _save_auth_users(users)
                st.success("Account created successfully! Go to the Login tab to sign in.")

    with forgot_tab:
        with st.form("forgot_password_form"):
            reset_username = st.text_input("Username", placeholder="Enter your username", key="reset_username")
            reset_email = st.text_input("Registered Email", placeholder="Enter your registered email", key="reset_email")
            reset_password = st.text_input("New Password", type="password", placeholder="Minimum 6 characters", key="reset_password")
            reset_confirm = st.text_input("Confirm New Password", type="password", placeholder="Re-enter your new password", key="reset_confirm")
            reset = st.form_submit_button("Reset Password", type="primary", width="stretch")

        if reset:
            username_key = reset_username.strip().lower()
            email_key = reset_email.strip().lower()
            record = users.get(username_key)

            if not record or record.get("email", "").lower() != email_key:
                st.error("Username and registered email do not match.")
            elif len(reset_password) < 6:
                st.error("New password must contain at least 6 characters.")
            elif reset_password != reset_confirm:
                st.error("Passwords do not match.")
            else:
                record["password"] = _hash_password(reset_password)
                users[username_key] = record
                _save_auth_users(users)
                st.success("Password reset successfully! You can now log in with your new password.")

    st.caption("Demo/local authentication: account details are stored in a local auth_users.json file. This is suitable for a college project demo, not production security.")

if not st.session_state.logged_in:
    _show_auth_page()
    st.stop()

# ================= END AUTHENTICATION SYSTEM =================
from scholarship_data import CATEGORY_COLORS, DOCUMENT_CHECKLIST, GENDERS, SCHOLARSHIPS, STATES, STREAMS, TODAY
from eligibility import BORDERLINE, ELIGIBLE, NOT_ELIGIBLE, VERDICT_LABEL, VERDICT_ORDER, evaluate, smallest_change
from scoring import feature_importance, ml_score, model_report, rule_based_score, score_reasons
from storage import load_user_data as _storage_load_user_data, save_user_data as _storage_save_user_data
from styles import CSS

# Store dashboard data separately for each logged-in account.
USER_DATA_DIR = Path(__file__).with_name("user_data")
USER_DATA_DIR.mkdir(exist_ok=True)

def _current_user_data_file():
    username = st.session_state.get("auth_user") or "guest"
    safe_username = "".join(ch for ch in username if ch.isalnum() or ch in "_-.")
    return USER_DATA_DIR / f"{safe_username}.json"

def load_user_data():
    user_file = _current_user_data_file()
    if user_file.exists():
        try:
            with user_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}
    # Preserve the existing demo data for the first account after authentication is added.
    return _storage_load_user_data()

def save_user_data(data):
    user_file = _current_user_data_file()
    try:
        with user_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=list)
    except OSError:
        # Fall back to the project's original storage behavior if local per-user storage is unavailable.
        _storage_save_user_data(data)

st.markdown(CSS, unsafe_allow_html=True)

PAGES = [
    "🏠 Overview", "📝 Profile", "📊 My Matches", "🔎 Discover",
    "📋 Applications", "📁 Documents", "⏰ Deadlines", "📈 Insights", "🔮 What-if",
    "⚖️ Compare", "🤖 Assistant", "🧠 Scoring"
]
if "_goto" in st.session_state:
    st.session_state["nav"] = st.session_state.pop("_goto")

NAME_TO_ID = {s["name"]: s["id"] for s in SCHOLARSHIPS}
ID_TO_SCHOLARSHIP = {s["id"]: s for s in SCHOLARSHIPS}

if "bootstrapped" not in st.session_state:
    saved = load_user_data()
    st.session_state.profile = saved.get("profile")
    st.session_state.saved = set(saved.get("saved", []))
    st.session_state.doc_checks = saved.get("doc_checks", {})
    st.session_state.compare = saved.get("compare", [])
    st.session_state.statuses = saved.get("statuses", {})
    st.session_state.chat_history = []
    st.session_state.nav = PAGES[0]
    st.session_state.bootstrapped = True


def persist():
    save_user_data({
        "profile": st.session_state.profile,
        "saved": list(st.session_state.saved),
        "doc_checks": st.session_state.doc_checks,
        "compare": st.session_state.compare,
        "statuses": st.session_state.statuses,
    })


def goto(page):
    st.session_state["_goto"] = page


def deadline_info(deadline_str):
    d = date.fromisoformat(deadline_str)
    days = (d - TODAY).days
    pretty = d.strftime("%d %b %Y")
    if days < 0: return f"Closed · {pretty}", "past", days
    if days == 0: return f"Due today · {pretty}", "urgent", days
    if days <= 7: return f"{days} days left · {pretty}", "urgent", days
    if days <= 30: return f"{days} days left · {pretty}", "soon", days
    return f"{days} days left · {pretty}", "plenty", days


def ranked_scholarships(profile, use_ml=False):
    """Every scholarship with its verdict. Sorted: eligible first, then borderline, then not eligible."""
    out = []
    for s in SCHOLARSHIPS:
        x = dict(s)
        x["closed"] = deadline_info(s["deadline"])[2] < 0
        if profile:
            ev = evaluate(profile, s)
            x["verdict"], x["checks"], x["rule_score"] = ev["verdict"], ev["checks"], ev["score"]
            x["ml_conf"] = ml_score(profile, s)
            x["score"] = x["ml_conf"] if use_ml else x["rule_score"]
            x["exact"] = ev["verdict"] == ELIGIBLE
        else:
            x.update({"verdict": NOT_ELIGIBLE, "checks": [], "rule_score": 0, "ml_conf": 0, "score": 0, "exact": False})
        out.append(x)
    return sorted(out, key=lambda x: (x["closed"], VERDICT_ORDER[x["verdict"]], -x["score"], -x["amount_value"]))

def viable(ranked):
    """Only scholarships worth acting on (eligible or borderline)."""
    return [x for x in ranked if x["verdict"] != NOT_ELIGIBLE and not x["closed"]]

def verdict_text(profile, s):
    return VERDICT_LABEL[evaluate(profile, s)["verdict"]][0] if profile else "—"


def toggle_save(sid):
    if sid in st.session_state.saved:
        st.session_state.saved.remove(sid)
        st.session_state.statuses.pop(str(sid), None)
    else: st.session_state.saved.add(sid)
    persist()


def render_card(s, key, profile):
    ev = evaluate(profile, s) if profile else None
    score = s.get("score", ev["score"]) if profile else None
    label, tone = VERDICT_LABEL[ev["verdict"]] if profile else ("Build profile", "muted")
    color = CATEGORY_COLORS.get(s["category"], "#635BFF")
    with st.container(border=True):
        a, b = st.columns([5.2, 1.8])
        with a:
            st.markdown(
                f"<span class='badge' style='background:{color}'>{s['category']}</span> "
                f"<span class='provider'>{s['provider']}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"<div class='sch-name' style='margin-top:.55rem'>{s['name']}</div>", unsafe_allow_html=True)
            st.caption(s["description"])
            dl, cls, days = deadline_info(s["deadline"])
            st.markdown(
                f"<span class='deadline-pill'>⏳ {dl}</span> "
                f"<span class='provider' style='margin-left:.35rem'>{s['amount']}</span>",
                unsafe_allow_html=True,
            )
        with b:
            if score is not None:
                st.markdown(f"<div class='score-pill'>{label}</div>", unsafe_allow_html=True)
                st.progress(score / 100)
                st.caption(f"Ranking score {score}")
            else:
                st.caption("Complete your profile to calculate a personalized match.")
            c1, c2 = st.columns(2)
            with c1:
                saved = s["id"] in st.session_state.saved
                if st.button("★ Saved" if saved else "☆ Save", key=f"{key}_save_{s['id']}", width="stretch"):
                    toggle_save(s["id"]); st.rerun()
            with c2:
                checked = s["id"] in st.session_state.compare
                val = st.checkbox("Compare", value=checked, key=f"{key}_cmp_{s['id']}")
                if val != checked:
                    if val and len(st.session_state.compare) < 4: st.session_state.compare.append(s["id"])
                    elif not val and s["id"] in st.session_state.compare: st.session_state.compare.remove(s["id"])
                    persist(); st.rerun()
            if s.get("source_url"):
                st.link_button("Apply / official page ↗", s["source_url"], disabled=days < 0, width="stretch")
            else:
                st.caption("Official page not added yet")
        with st.expander("Eligibility details & documents"):
            q1, q2, q3 = st.columns(3)
            q1.metric("Income limit", f"₹{s['income_limit']:,}")
            q2.metric("Academic minimum", s["min_academic"])
            q3.metric("Deadline", date.fromisoformat(s["deadline"]).strftime("%d %b"))
            st.markdown("**Required documents**")
            st.write(" · ".join(s["docs"]))
            if s.get("source_url"): st.markdown(f"Source: [{s['source_url']}]({s['source_url']})")
            if s.get("last_verified"): st.caption(f"✅ Rules checked against an official source on {s['last_verified']}. Deadlines can change, so confirm on the provider's site.")
            else: st.caption("⚠️ Unverified: based on secondary sources. Confirm on the provider's site before applying.")
            if s.get("note"): st.caption("ℹ️ " + s["note"])
            if profile:
                st.markdown("<div class=\"match-breakdown-title\">WHY THIS VERDICT? (rule by rule)</div>", unsafe_allow_html=True)
                for reason in score_reasons(profile, s):
                    st.markdown(f"<div class=\"reason-row\">{reason}</div>", unsafe_allow_html=True)
                st.caption(f"The verdict comes from the rules above. Experimental chance of being selected: about {ml_score(profile,s)}% (trained on synthetic data, can never override the verdict)")


# Sidebar
with st.sidebar:

    st.markdown("<div class='brand'><div class='brand-mark'>S</div><div><b>ScholarAI</b><small>Smart scholarship finder</small></div></div>", unsafe_allow_html=True)
    st.radio("Navigation", PAGES, key="nav", label_visibility="collapsed")
    st.divider()
    if st.session_state.profile:
        p = st.session_state.profile
        completeness = sum(bool(p.get(k)) for k in ["course","year","category","income","academic","family"]) / 6
        st.markdown(f"<div class='side-profile'><b>{html.escape(p['course'])}</b><br>{p['year']} · {p['category']}<br><span>Profile completeness</span></div>", unsafe_allow_html=True)
        st.progress(completeness, text=f"{round(completeness*100)}% complete")
        if st.button("Edit profile", width="stretch"): goto("📝 Profile"); st.rerun()
    else:
        st.info("Build your profile to unlock personalized matches.")
        if st.button("Build my profile →", type="primary", width="stretch"): goto("📝 Profile"); st.rerun()
    st.divider()
    st.caption(f"Signed in as **{html.escape(st.session_state.get('auth_user') or 'student')}**")
    if st.button("🚪 Logout", width="stretch"):
        st.session_state.logged_in = False
        st.session_state.auth_user = None
        st.rerun()
    st.divider()
    st.caption(f"☆ {len(st.session_state.saved)} saved  ·  ⚖️ {len(st.session_state.compare)} comparing")
    if st.button("Reset demo data", width="stretch"):
        save_user_data({}); st.session_state.clear(); st.rerun()
    st.caption("Demo project · verify current rules with official providers.")

page = st.session_state.nav
profile = st.session_state.profile
PROFILE_KEYS = ["course", "year", "category", "income", "academic", "family"]
profile_pct = round(sum(bool((profile or {}).get(k)) for k in PROFILE_KEYS) / len(PROFILE_KEYS) * 100)
docs_pct = round(sum(st.session_state.doc_checks.values()) / len(DOCUMENT_CHECKLIST) * 100)

# Overview



if page == "🏠 Overview":
    ranked = ranked_scholarships(profile)
    matches = sum(x["verdict"] == ELIGIBLE and not x["closed"] for x in ranked) if profile else 0
    soon = sum(0 <= deadline_info(s["deadline"])[2] <= 30 for s in SCHOLARSHIPS)
    docs_done = sum(st.session_state.doc_checks.values())
    docs_pct = round(docs_done / len(DOCUMENT_CHECKLIST) * 100)
    best = viable(ranked)[0] if (profile and viable(ranked)) else None
    top_score = best["score"] if best else 0
    top_name = best["name"] if best else ("No eligible scholarship yet" if profile else "Complete your profile")
    first = (profile or {}).get("name") or "Student"
    initials = "".join(x[0] for x in first.split()[:2]).upper() or "S"

    st.markdown(f"""
    <div class="sa-topbar">
      <div>
        <div class="sa-greeting">GOOD MORNING, {initials} ✦</div>
        <h1>Find funding that fits <span>your future.</span></h1>
        <p>One focused workspace for discovering scholarships, understanding your match and staying application-ready.</p>
      </div>
      <div class="sa-user-chip"><span class="sa-avatar">{initials}</span><span><b>{html.escape(first)}</b><small>{(profile or {}).get('year','Build your profile')}</small></span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sa-hero-v2">
      <div class="hero-copy">
        <div class="hero-eyebrow">SCHOLARAI · PERSONALIZED FUNDING HUB</div>
        <h2>Turn your profile into <span>opportunity.</span></h2>
        <p>See your strongest scholarship matches, upcoming deadlines and what you still need to finish before applying.</p>
        <div class="hero-actions"><span class="hero-trust">✓ Explainable matching</span><span class="hero-trust">✓ Deadline-aware</span><span class="hero-trust">✓ Local progress</span></div>
      </div>
      <div class="hero-orbit">
        <div class="orbit-ring"></div><div class="orbit-ring ring-2"></div>
        <div class="orbit-core"><small>TOP MATCH</small><strong>{top_score}%</strong><span>{'Personalized' if profile else 'Not calculated'}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="sa-section-head"><div><span>YOUR WORKSPACE</span><h3>Everything you need to move from match to application</h3></div></div>
    <div class="feature-strip">
      <div class="action-card"><b>🎯 Personalized matching</b><p>Understand your score and the eligibility factors behind it.</p></div>
      <div class="action-card"><b>⏰ Deadline intelligence</b><p>See countdowns and prioritize scholarships closing soon.</p></div>
      <div class="action-card"><b>📋 Application readiness</b><p>Track profile, documents and application progress in one place.</p></div>
    </div>
    """, unsafe_allow_html=True)

    action1, action2, action3 = st.columns([1.25,1.25,3.5])
    with action1:
        if st.button("✨ Start eligibility check", type="primary", width="stretch"):
            goto("📝 Profile"); st.rerun()
    with action2:
        if st.button("🔎 Explore scholarships", width="stretch"):
            goto("🔎 Discover"); st.rerun()
    with action3:
        q=st.text_input("Quick search", placeholder="Search scholarships, providers or keywords…", label_visibility="collapsed")
        if q:
            goto("🔎 Discover"); st.session_state.quick_search=q; st.rerun()

    kpi_data=[
        ("🎯","Eligible now",str(matches),"Based on your profile" if profile else "Build your profile first","violet"),
        ("⏰","Closing soon",str(soon),"Deadlines within 30 days","orange"),
        ("♡","Saved",str(len(st.session_state.saved)),"Opportunities in your shortlist","pink"),
        ("✓","Ready",f"{docs_pct}%","Document readiness","cyan"),
    ]
    k=st.columns(4)
    for col,(icon,label,val,sub,tone) in zip(k,kpi_data):
        col.markdown(f"<div class='sa-kpi {tone}'><div class='kpi-icon'>{icon}</div><div><span>{label}</span><strong>{val}</strong><small>{sub}</small></div></div>",unsafe_allow_html=True)

    st.markdown("<div class='sa-section-head'><div><span>YOUR DASHBOARD</span><h3>At a glance</h3></div><div class='section-link'>Live demo workspace</div></div>",unsafe_allow_html=True)
    left,right=st.columns([1.05,1.95],gap="large")
    with left:
        ring=top_score if profile else 0
        st.markdown(f"""
        <div class="sa-panel match-card">
          <div class="panel-top"><div><span class="panel-label">MATCH HEALTH</span><h3>Your fit score</h3></div><span class="status-dot">● LIVE</span></div>
          <div class="big-ring" style="--score:{ring*3.6}deg"><div><strong>{ring}%</strong><small>{'Build profile' if not profile else 'Eligible' if ring>=70 else 'Borderline' if ring>=50 else 'No match yet'}</small></div></div>
          <p class="panel-muted">{top_name if profile else 'Complete your profile to unlock personalized scholarship matching.'}</p>
          <div class="mini-progress"><span style="width:{min(ring,100)}%"></span></div>
          <div class="mini-row"><span>Profile completeness</span><b>{round(sum(bool((profile or {}).get(k)) for k in ['course','year','category','income','academic','family'])/6*100)}%</b></div>
        </div>
        """,unsafe_allow_html=True)
    with right:
        upcoming=sorted([s for s in SCHOLARSHIPS if deadline_info(s["deadline"])[2]>=0],key=lambda x:deadline_info(x["deadline"])[2])[:4]
        rows=""
        for s in upcoming:
            dl,cls,days=deadline_info(s["deadline"])
            rows+=f"<div class='deadline-row'><div class='deadline-avatar'>{s['name'][0]}</div><div class='deadline-name'><b>{s['name']}</b><small>{s['provider']}</small></div><span class='deadline-count {cls}'>{days}d</span><button class='fake-link'>View</button></div>"
        st.markdown(f"""
        <div class="sa-panel deadlines-panel">
          <div class="panel-top"><div><span class="panel-label">TIME SENSITIVE</span><h3>Closing soon</h3></div><span class="count-badge">{len(upcoming)} open</span></div>
          {rows}
        </div>
        """,unsafe_allow_html=True)

    st.markdown("<div class='sa-section-head'><div><span>CURATED FOR YOU</span><h3>Recommended for you</h3></div></div>",unsafe_allow_html=True)
    recs = viable(ranked)[:3] if profile else sorted(SCHOLARSHIPS,key=lambda x:x['amount_value'],reverse=True)[:3]
    if profile and not recs: st.info('No scholarship fits your profile right now. Check Discover for details on each one.')
    rc=st.columns(3,gap="medium")
    for i,(col,s) in enumerate(zip(rc,recs)):
        score=s.get('score',0) if profile else 0
        color=['violet','pink','cyan'][i]
        dl,cls,days=deadline_info(s['deadline'])
        with col:
            st.markdown(f"""
            <div class='sa-scholar-card {color}'>
              <div class='sch-top'><span class='category-tag'>{s['category']}</span><span class='save-dot'>♡</span></div>
              <h4>{s['name']}</h4><p>{s['provider']}</p>
              <div class='sch-amount'>{s['amount']}</div>
              <div class='sch-meta'><span>⏱ {days} days</span><span>₹{s['income_limit']:,} limit</span></div>
              <div class='sch-bottom'><span>{VERDICT_LABEL[s['verdict']][0] if profile else 'Build profile'}</span><b>{'→'}</b></div>
            </div>
            """,unsafe_allow_html=True)
            if st.button("View scholarship",key=f"home_view_{s['id']}",width="stretch"):
                st.session_state["focus_id"] = s["id"]; goto("🔎 Discover"); st.rerun()

    # Smart next-actions / notification center
    st.markdown("""
    <div class="feature-strip">
      <div class="feature-strip-head">
        <div><span>SMART ACTION CENTER</span><h3>Your next best actions</h3></div>
        <small>Personalized from your profile, shortlist and deadlines</small>
      </div>
    </div>
    """, unsafe_allow_html=True)

    action_items = []
    profile_pct = round(sum(bool((profile or {}).get(k)) for k in ["course","year","category","income","academic","family"]) / 6 * 100)
    if not profile:
        action_items.append(("🎯","Build your profile","Unlock personalized matching and eligibility explanations.","📝 Profile","violet"))
    elif profile_pct < 100:
        action_items.append(("✨","Complete your profile",f"You're at {profile_pct}%. Finish the remaining details for better matches.","📝 Profile","violet"))
    if profile:
        needed = sorted({d for s in viable(ranked)[:3] for d in s["docs"]})
        missing = [d for d in needed if not st.session_state.doc_checks.get(d)]
        if missing:
            action_items.append(("📄","Upload a priority document",f"{missing[0]} is needed by one of your top matches.","📁 Documents","pink"))
    soonest = sorted([s for s in SCHOLARSHIPS if deadline_info(s["deadline"])[2] >= 0], key=lambda s: deadline_info(s["deadline"])[2])
    if soonest:
        s0 = soonest[0]
        action_items.append(("⏰","Deadline approaching",f"{s0['name']} closes in {deadline_info(s0['deadline'])[2]} days.","⏰ Deadlines","orange"))
    if not st.session_state.saved:
        action_items.append(("♡","Create a shortlist","Save scholarships so you can compare and track applications.","🔎 Discover","cyan"))
    if not action_items:
        action_items.append(("🚀","You're application-ready","Review your strongest match and move it into your application pipeline.","📋 Applications","violet"))

    acols = st.columns(min(3, len(action_items)), gap="medium")
    for i, item in enumerate(action_items[:3]):
        icon, title, desc, target, tone = item
        with acols[i]:
            st.markdown(f"<div class='action-card {tone}'><div class='action-icon'>{icon}</div><b>{title}</b><p>{desc}</p></div>", unsafe_allow_html=True)
            if st.button("Take action →", key=f"action_{i}", width="stretch"):
                goto(target); st.rerun()

    st.markdown("<div class='sa-section-head'><div><span>APPLICATION READINESS</span><h3>Finish stronger</h3></div></div>",unsafe_allow_html=True)
    r1,r2,r3=st.columns(3)
    readiness=[("Profile","Tell ScholarAI who you are",round(sum(bool((profile or {}).get(k)) for k in ['course','year','category','income','academic','family'])/6*100),"🧑‍🎓","📝 Profile"),("Documents","Keep your core documents ready",docs_pct,"📄","📁 Documents"),("Shortlist","Save scholarships you want to revisit",min(100,len(st.session_state.saved)*25),"♡","🔎 Discover")]
    for col,(title,desc,pct,icon,target) in zip([r1,r2,r3],readiness):
        with col:
            st.markdown(f"<div class='sa-readiness'><div class='ready-icon'>{icon}</div><div class='ready-copy'><b>{title}</b><small>{desc}</small><div class='ready-bar'><span style='width:{pct}%'></span></div><em>{pct}% complete</em></div></div>",unsafe_allow_html=True)
            if st.button("Continue →",key=f"ready_{title}",width="stretch"):
                goto(target); st.rerun()

# Profile
elif page == "📝 Profile":
    st.markdown("<div class='page-head'><div class='eyebrow'>STEP 01</div><h2>Build your student profile</h2><p>Use real values for a more useful demonstration. You can edit these details anytime.</p></div>", unsafe_allow_html=True)
    DEMO = dict(name="Demo Student", cgpa=0.0, gender="Female", state="Maharashtra", stream="STEM", first_gen=False, age=20, course="B.Sc. Data Science", year="TY", category="General", income=180000, academic=82.0, occupation="Salaried", family=4, minority=False, disability=False, domicile=True, female=True)
    if st.button("✨ Load demo profile"): [st.session_state.__setitem__(f"f_{k}",v) for k,v in DEMO.items()]; st.rerun()
    p = profile or {}
    with st.form("profile_form"):
        st.markdown("#### Personal & academic")
        name = st.text_input("Your name", st.session_state.get("f_name", p.get("name", "")), placeholder="e.g. Aarav Sharma", key="f_name")
        a,b,c = st.columns(3)
        age = a.number_input("Age",15,60,int(st.session_state.get("f_age",p.get("age",20))),key="f_age")
        course = b.text_input("Degree / course",st.session_state.get("f_course",p.get("course","")),placeholder="e.g. B.Sc. Data Science",key="f_course")
        year = c.selectbox("Year of study",["FY","SY","TY","Graduate"],index=["FY","SY","TY","Graduate"].index(st.session_state.get("f_year",p.get("year","TY"))),key="f_year")
        a,b,c = st.columns(3)
        academic = a.number_input("Marks (percentage)",0.0,100.0,float(st.session_state.get("f_academic",p.get("academic",75.0))),step=.5,key="f_academic")
        income = b.number_input("Annual family income (₹)",0,5000000,int(st.session_state.get("f_income",p.get("income",250000))),step=5000,key="f_income")
        family = c.number_input("Family members",1,20,int(st.session_state.get("f_family",p.get("family",4))),key="f_family")
        a,b = st.columns(2)
        cgpa = a.number_input("Or enter CGPA (out of 10, optional)",0.0,10.0,float(st.session_state.get("f_cgpa",p.get("cgpa",0.0))),step=.1,key="f_cgpa")
        b.caption("If you enter a CGPA, it is converted with the common 9.5 × CGPA rule (your college may use another formula). Leave it at 0 to use the percentage.")
        a,b = st.columns(2)
        category = a.selectbox("Category",["General","OBC","SC","ST","EWS"],index=["General","OBC","SC","ST","EWS"].index(st.session_state.get("f_category",p.get("category","General"))),key="f_category")
        occupation = b.text_input("Parent / guardian occupation",st.session_state.get("f_occupation",p.get("occupation","")),key="f_occupation")
        st.markdown("#### Special eligibility")
        a,b,c = st.columns(3)
        gender = a.selectbox("Gender", GENDERS, index=GENDERS.index(st.session_state.get("f_gender", p.get("gender", GENDERS[0]))), key="f_gender")
        state = b.selectbox("Home state", STATES, index=STATES.index(st.session_state.get("f_state", p.get("state", "Maharashtra"))), key="f_state")
        stream = c.selectbox("Field of study", STREAMS, index=STREAMS.index(st.session_state.get("f_stream", p.get("stream", STREAMS[0]))), key="f_stream")
        a,b,c = st.columns(3)
        minority = a.checkbox("Minority community", st.session_state.get("f_minority", p.get("minority", False)), key="f_minority")
        disability = b.checkbox("Disability of 40% or more", st.session_state.get("f_disability", p.get("disability", False)), key="f_disability")
        first_gen = c.checkbox("First in family to attend college", st.session_state.get("f_first_gen", p.get("first_gen", False)), key="f_first_gen")
        submitted=st.form_submit_button("Analyze eligibility →",type="primary",width="stretch")
    if submitted:
        if not course.strip(): st.error("Please enter your degree / course.")
        else:
            st.session_state.profile={"name":name.strip(), "age":int(age),"course":course.strip(),"year":year,"category":category,"income":int(income),"academic":(round(cgpa*9.5,1) if cgpa > 0 else float(academic)),"cgpa":float(cgpa),"occupation":occupation.strip(),"family":int(family),"minority":minority,"disability":disability,"gender":gender,"state":state,"stream":stream,"first_gen":first_gen,"domicile":state=="Maharashtra","female":gender=="Female"}
            persist(); goto("📊 My Matches"); st.rerun()


elif page == "📊 My Matches":
    st.markdown("<div class='page-head'><div class='eyebrow'>STEP 02</div><h2>Your personalized matches</h2><p>Each scholarship gets a clear verdict, explained rule by rule. The ML score is experimental and can never override a verdict.</p></div>", unsafe_allow_html=True)
    if not profile:
        st.warning("Build your profile first.")
        if st.button("Build profile →",type="primary"): goto("📝 Profile"); st.rerun()
        st.stop()
    use_ml=st.toggle("Rank by experimental selection chance (synthetic-data model)",False)
    ranked=ranked_scholarships(profile,use_ml)
    elig=[x for x in ranked if x["verdict"]==ELIGIBLE and not x["closed"]]
    near=[x for x in ranked if x["verdict"]==BORDERLINE and not x["closed"]]
    closed=[x for x in ranked if x["closed"] and x["verdict"]!=NOT_ELIGIBLE]    
    no=[x for x in ranked if x["verdict"]==NOT_ELIGIBLE]
    a,b,c,d=st.columns(4)
    a.metric("✅ Eligible",len(elig)); b.metric("🟡 Borderline",len(near)); c.metric("❌ Not eligible",len(no)); d.metric("Saved",len(st.session_state.saved))
    bar_color={ELIGIBLE:"#16a34a",BORDERLINE:"#f59e0b",NOT_ELIGIBLE:"#ef4444"}
    fig=go.Figure(go.Bar(x=[x["score"] for x in ranked[:7]],y=[x["name"] for x in ranked[:7]],orientation="h",marker_color=[bar_color[x["verdict"]] for x in ranked[:7]],text=[f"{x['score']}" for x in ranked[:7]],textposition="outside"))
    fig.update_layout(height=330,margin=dict(l=10,r=60,t=10,b=20),xaxis=dict(range=[0,110],title="Ranking score (green = eligible, amber = borderline, red = not eligible)"),yaxis=dict(autorange="reversed"),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig,width="stretch")
    if elig:
        st.markdown("### ✅ You are eligible")
        for s in elig: render_card(s,"res",profile)
    else:
        st.info("No scholarship fully fits your profile right now. Look at the borderline ones below, they are close.")
    if near:
        st.markdown("### 🟡 Borderline: close to qualifying")
        for s in near: render_card(s,"res",profile)
    if closed:
        st.markdown(f"### ⏰ Closed: you would have qualified ({len(closed)})")
        for s in closed:
            st.markdown(f"**{s['name']}**: closed on {date.fromisoformat(s['deadline']).strftime('%d %b %Y')}. Check the provider's site for next year's window.")
    if no:
        st.markdown(f"### ❌ Not eligible ({len(no)})")
        for s in no:
            failed=[c["text"] for c in s["checks"] if c["status"]=="fail"]
            st.markdown(f"**{s['name']}**: " + " ".join(failed))
    report=io.StringIO(); report.write("ScholarAI Eligibility Report\n===========================\n"); report.write(f"Generated: {date.today():%d %b %Y}\nCourse: {profile['course']} ({profile['year']})\nAcademic: {profile['academic']}\nIncome: Rs {profile['income']:,}\n\n")
    for s in ranked: report.write(f"- {s['name']} | {VERDICT_LABEL[s['verdict']][0]} | deadline {s['deadline']}\n")
    st.download_button("⬇️ Export results (.txt)",report.getvalue(),"scholarai_report.txt","text/plain")

# Discover
elif page == "🔎 Discover":
    st.markdown("<div class='page-head'><div class='eyebrow'>SCHOLARSHIP LIBRARY</div><h2>Discover opportunities</h2><p>Search, filter and save scholarships before comparing them.</p></div>", unsafe_allow_html=True)
    a,b,c,d=st.columns([2,1,1,1])
    q=a.text_input("Search",value=st.session_state.pop("quick_search", ""),placeholder="Scholarship, provider, keyword…")
    cats=sorted({s['category'] for s in SCHOLARSHIPS}); cat=b.multiselect("Category",cats)
    max_income=c.number_input("Income limit ≥",0,5000000,0,50000)
    sort=d.selectbox("Sort by",["Best match","Deadline","Amount"])
    filtered=[s for s in SCHOLARSHIPS if (not q or q.lower() in (s['name']+' '+s['provider']+' '+s['description']).lower()) and (not cat or s['category'] in cat) and s['income_limit']>=max_income]
    if profile:
        scored={x["id"]:x for x in ranked_scholarships(profile)}
        filtered=[scored[s["id"]] for s in filtered]
        if sort=="Best match": filtered.sort(key=lambda x:(x["closed"],VERDICT_ORDER[x["verdict"]],-x["score"],-x["amount_value"]))
    if sort=="Deadline": filtered=sorted(filtered,key=lambda s:deadline_info(s['deadline'])[2])
    if sort=="Amount": filtered=sorted(filtered,key=lambda s:s['amount_value'],reverse=True)
    st.caption(f"{len(filtered)} opportunities")
    focus_id = st.session_state.get("focus_id")
    if focus_id in ID_TO_SCHOLARSHIP:
        focus = next((x for x in filtered if x["id"] == focus_id), None) or ID_TO_SCHOLARSHIP[focus_id]
        st.markdown("### 📌 You opened this scholarship")
        render_card(focus, "focus", profile)
        if st.button("Clear and show all"):
            st.session_state.pop("focus_id", None); st.rerun()
        st.markdown("### All scholarships")
    for s in filtered: render_card(s,"disc",profile)

# Compare
elif page == "⚖️ Compare":
    st.markdown("<div class='page-head'><div class='eyebrow'>DECISION SUPPORT</div><h2>Compare scholarships</h2><p>Place up to four opportunities side by side.</p></div>",unsafe_allow_html=True)
    default=[next((n for n,i in NAME_TO_ID.items() if i==sid),None) for sid in st.session_state.compare]
    names=st.multiselect("Select scholarships",list(NAME_TO_ID),default=[x for x in default if x],max_selections=4)
    st.session_state.compare=[NAME_TO_ID[n] for n in names]; persist()
    if names:
        rows=[]
        for n in names:
            s=ID_TO_SCHOLARSHIP[NAME_TO_ID[n]]
            rows.append({"Scholarship":n,"Category":s['category'],"Provider":s['provider'],"Income limit":f"₹{s['income_limit']:,}","Academic minimum":s['min_academic'],"Amount":s['amount'],"Deadline":date.fromisoformat(s['deadline']).strftime('%d %b %Y'),"Your verdict":verdict_text(profile,s)})
        st.dataframe(pd.DataFrame(rows).set_index("Scholarship"),width="stretch")
    else: st.info("Select scholarships above to compare.")

# Documents
elif page == "📁 Documents":
    st.markdown("<div class='page-head'><div class='eyebrow'>DOCUMENT VAULT</div><h2>Keep every application document ready</h2><p>Track what is ready, what is missing and which scholarships need each document.</p></div>", unsafe_allow_html=True)
    done=sum(st.session_state.doc_checks.values()); pct=round(done/len(DOCUMENT_CHECKLIST)*100)
    st.markdown(f"<div class='vault-summary'><div><span>DOCUMENT READINESS</span><b>{pct}%</b></div><div class='vault-track'><span style='width:{pct}%'></span></div><small>{done} of {len(DOCUMENT_CHECKLIST)} core documents checked</small></div>", unsafe_allow_html=True)
    if profile:
        top3 = viable(ranked_scholarships(profile))[:3]
        doc_usage = {}
        for s in top3:
            for d in s["docs"]:
                doc_usage.setdefault(d, []).append(s["name"])
    cols=st.columns(2)
    for i,doc in enumerate(DOCUMENT_CHECKLIST):
        cur=st.session_state.doc_checks.get(doc,False)
        usage = doc_usage.get(doc, []) if profile else []
        with cols[i%2]:
            status_text = "READY" if cur else "MISSING"
            st.markdown(f"<div class='doc-vault-card {'ready' if cur else 'missing'}'><div class='doc-icon'>{'✓' if cur else '○'}</div><div><b>{doc}</b><small>{status_text} · {len(usage)} top-match use(s)</small></div></div>", unsafe_allow_html=True)
            val=st.checkbox("Mark ready",cur,key=f"doc_{i}")
            if val!=cur: st.session_state.doc_checks[doc]=val; persist()
    if profile:
        st.markdown("### Priority documents for your top matches")
        needed = sorted({d for s in viable(ranked_scholarships(profile))[:3] for d in s["docs"]})
        for d in needed:
            status = "Ready" if st.session_state.doc_checks.get(d) else "Still needed"
            st.markdown(f"<div class='priority-doc'><span>{'✓' if status=='Ready' else '○'}</span><b>{d}</b><small>{status}</small></div>", unsafe_allow_html=True)

# Tracker
elif page == "📋 Applications":
    st.markdown("<div class='page-head'><div class='eyebrow'>APPLICATION PIPELINE</div><h2>Move opportunities from idea to submitted</h2><p>Your scholarship workflow, organized in one place.</p></div>", unsafe_allow_html=True)
    saved = [ID_TO_SCHOLARSHIP[i] for i in st.session_state.saved if i in ID_TO_SCHOLARSHIP]
    statuses = ["Interested", "Preparing", "Ready to submit", "Submitted"]
    cols = st.columns(4, gap="small")
    for col, status in zip(cols, statuses):
        items = [s for s in saved if st.session_state.statuses.get(str(s["id"]), "Interested") == status]
        with col:
            st.markdown(f"<div class='kanban-head'><b>{status}</b><span>{len(items)}</span></div>", unsafe_allow_html=True)
            if not items:
                st.markdown("<div class='empty-kanban'>No scholarships here yet.</div>", unsafe_allow_html=True)
            for s in items:
                dl, cls, days = deadline_info(s["deadline"])
                vt = verdict_text(profile, s)
                st.markdown(f"""
                <div class='kanban-card'>
                  <span class='category-tag'>{s['category']}</span>
                  <b>{s['name']}</b>
                  <small>{s['provider']}</small>
                  <div class='kanban-meta'><span>{vt}</span><span>{days}d left</span></div>
                </div>
                """, unsafe_allow_html=True)
                idx = statuses.index(status)
                if idx < len(statuses) - 1:
                    if st.button("Move →", key=f"move_{s['id']}_{status}", width="stretch"):
                        st.session_state.statuses[str(s["id"])] = statuses[idx + 1]
                        persist(); st.rerun()
                if idx > 0:
                    if st.button("← Back", key=f"back_{s['id']}_{status}", width="stretch"):
                        st.session_state.statuses[str(s["id"])] = statuses[idx - 1]
                        persist(); st.rerun()
                if st.button("Remove", key=f"remove_{s['id']}_{status}", width="stretch"):
                    toggle_save(s["id"]); st.rerun()
                if st.button("Open", key=f"open_app_{s['id']}", width="stretch"):
                    st.session_state["focus_id"] = s["id"]; goto("🔎 Discover"); st.rerun()    
                    st.markdown("### Application checklist")
    checklist = [
        ("Profile complete", profile_pct if profile else 0),
        ("Priority documents", docs_pct),
        ("Shortlist created", min(100, len(saved) * 25)),
        ("Applications in progress", min(100, sum(st.session_state.statuses.get(str(s["id"]), "Interested") in ["Preparing","Ready to submit","Submitted"] for s in saved) * 25)),
    ]
    for label, pct in checklist:
        st.markdown(f"<div class='check-row'><span>{label}</span><b>{pct}%</b></div><div class='check-bar'><span style='width:{pct}%'></span></div>", unsafe_allow_html=True)

# Deadline Intelligence
elif page == "⏰ Deadlines":
    st.markdown("<div class='page-head'><div class='eyebrow'>DEADLINE INTELLIGENCE</div><h2>Never lose an opportunity to a deadline</h2><p>Prioritize open scholarships by urgency and your match quality.</p></div>", unsafe_allow_html=True)
    window = st.select_slider("Show deadlines within", options=[7, 14, 30, 60, 120], value=30, format_func=lambda x: f"{x} days")
    upcoming = [s for s in SCHOLARSHIPS if 0 <= deadline_info(s["deadline"])[2] <= window]
    upcoming = sorted(upcoming, key=lambda s: (deadline_info(s["deadline"])[2], -rule_based_score(profile, s) if profile else 0))
    if upcoming:
        for s in upcoming:
            days = deadline_info(s["deadline"])[2]
            vt = verdict_text(profile, s)
            urgency = "URGENT" if days <= 7 else "SOON" if days <= 30 else "UPCOMING"
            st.markdown(f"""
            <div class='deadline-intel'>
              <div class='deadline-priority {urgency.lower()}'>{urgency}</div>
              <div class='deadline-intel-main'><b>{s['name']}</b><small>{s['provider']} · {s['amount']}</small></div>
              <div class='deadline-score'><b>{vt}</b><small>verdict</small></div>
              <div class='deadline-days'><b>{days}</b><small>days left</small></div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("View opportunity", key=f"deadline_{s['id']}", width="stretch"):
                goto("🔎 Discover"); st.rerun()
    else:
        st.success("No scholarships are closing inside the selected window.")

# Insights
elif page == "📈 Insights":
    st.markdown("<div class='page-head'><div class='eyebrow'>STUDENT INSIGHTS</div><h2>Understand your scholarship portfolio</h2><p>Compact analytics for matching, readiness, deadlines and potential funding.</p></div>", unsafe_allow_html=True)
    ranked = ranked_scholarships(profile) if profile else []
    potential = sum(s["amount_value"] for s in ranked if s["verdict"] == ELIGIBLE and not s["closed"]) if ranked else 0
    eligible = sum(s["verdict"] == ELIGIBLE and not s["closed"] for s in ranked) if ranked else 0 
    submitted = sum(st.session_state.statuses.get(str(i), "") == "Submitted" for i in st.session_state.saved)
    preparing = sum(st.session_state.statuses.get(str(i), "") in ["Preparing","Ready to submit"] for i in st.session_state.saved)
    a,b,c,d = st.columns(4)
    a.metric("Funding you qualify for", f"₹{potential:,}")
    b.metric("✅ Eligible", eligible)
    c.metric("In progress", preparing)
    d.metric("Submitted", submitted)

    if ranked:
        left,right = st.columns(2)
        with left:
            fig = go.Figure(go.Bar(x=[s["score"] for s in ranked[:7]], y=[s["name"] for s in ranked[:7]], orientation="h", marker_color=[{"eligible":"#16a34a","borderline":"#f59e0b","not_eligible":"#ef4444"}[s["verdict"]] for s in ranked[:7]], text=[f"{s['score']}" for s in ranked[:7]], textposition="outside"))
            fig.update_layout(height=360, margin=dict(l=10,r=60,t=20,b=20), xaxis=dict(range=[0,110],title="Ranking score (colour = verdict)"), yaxis=dict(autorange="reversed"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, width="stretch")
        with right:
            deadline_counts = {"≤7 days":0,"8–30 days":0,"31–60 days":0,"60+ days":0}
            for s in SCHOLARSHIPS:
                days = deadline_info(s["deadline"])[2]
                if days < 0: continue
                if days <= 7: deadline_counts["≤7 days"] += 1
                elif days <= 30: deadline_counts["8–30 days"] += 1
                elif days <= 60: deadline_counts["31–60 days"] += 1
                else: deadline_counts["60+ days"] += 1
            fig2 = go.Figure(go.Pie(labels=list(deadline_counts), values=list(deadline_counts.values()), hole=.62))
            fig2.update_layout(height=360, margin=dict(l=10,r=10,t=20,b=20), showlegend=True, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, width="stretch")
    else:
        st.info("Build your profile to unlock personalized analytics.")

# Assistant
elif page == "🤖 Assistant":
    st.markdown("<div class='page-head'><div class='eyebrow'>STUDENT SUPPORT</div><h2>ScholarAI Assistant</h2><p>A lightweight rule-based helper for this demo — not a live government support service.</p></div>",unsafe_allow_html=True)
    quick=["Which matches do I have?","What documents do I need?","Which deadlines are soon?","How do I improve my profile?"]
    fired=next((q for q in quick if st.button(q,key='q_'+q,width='stretch')),None)
    for role,text in st.session_state.chat_history:
        with st.chat_message(role): st.write(text)
    prompt=fired or st.chat_input("Ask about your matches, documents or deadlines…")
    if prompt:
        st.session_state.chat_history.append(("user",prompt)); low=prompt.lower(); ranked=ranked_scholarships(profile) if profile else []
        if "document" in low: ans="Your document center tracks common documents such as Aadhaar, income certificate, marksheets, domicile/category certificates, bonafide certificate and bank details. Exact requirements vary by scholarship."
        elif "deadline" in low: ans="The soonest open deadlines are: " + "; ".join(f"{s['name']} — {deadline_info(s['deadline'])[0]}" for s in sorted([x for x in SCHOLARSHIPS if deadline_info(x['deadline'])[2]>=0],key=lambda x:deadline_info(x['deadline'])[2])[:3])
        elif "improve" in low: ans="Use the Profile page to keep academic, income and eligibility information accurate, then review the explanation under each match. Completing documents early also reduces application friction."
        elif profile: v=viable(ranked)[:3]; ans=(("You are eligible or close to eligible for: " + ", ".join(s['name'] for s in v) + ". ") if v else "No scholarship in the list fits your profile right now. ") + "Always verify current eligibility on the official provider before applying."
        else: ans="Build your student profile first, then I can summarize your demo matches."
        st.session_state.chat_history.append(("assistant",ans)); st.rerun()

elif page == "🔮 What-if":
    st.markdown("<div class='page-head'><div class='eyebrow'>WHAT-IF</div><h2>What if my numbers change?</h2><p>Move the sliders and watch your verdicts change. Nothing here changes your saved profile.</p></div>", unsafe_allow_html=True)
    if not profile:
        st.warning("Build your profile first.")
        if st.button("Build profile →", type="primary"): goto("📝 Profile"); st.rerun()
        st.stop()
    top_income = max(2_000_000, int(profile["income"]))
    a, b = st.columns(2)
    new_income = a.slider("Family income (₹)", 0, top_income, int(profile["income"]), step=10_000)
    new_marks = b.slider("Marks / CGPA (%)", 0.0, 100.0, float(profile["academic"]), step=0.5)
    base = {x["id"]: x for x in ranked_scholarships(profile)}
    what = {x["id"]: x for x in ranked_scholarships({**profile, "income": new_income, "academic": new_marks})}
    count = lambda d, v: sum(x["verdict"] == v for x in d.values())
    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Eligible", count(what, ELIGIBLE), count(what, ELIGIBLE) - count(base, ELIGIBLE))
    c2.metric("🟡 Borderline", count(what, BORDERLINE), count(what, BORDERLINE) - count(base, BORDERLINE))
    c3.metric("❌ Not eligible", count(what, NOT_ELIGIBLE), count(what, NOT_ELIGIBLE) - count(base, NOT_ELIGIBLE), delta_color="inverse")
    st.markdown("### What changed")
    changed = [(base[i], what[i]) for i in base if base[i]["verdict"] != what[i]["verdict"]]
    if not changed:
        st.info("Nothing changes yet. Move a slider to see what happens.")
    for before, after in changed:
        st.markdown(f"**{after['name']}**: {VERDICT_LABEL[before['verdict']][0]} → {VERDICT_LABEL[after['verdict']][0]}")
    st.markdown("### Closest to qualifying")
    st.caption("Based on your saved profile. Only scholarships where income or marks are the gap are listed.")
    shown = 0
    for s in SCHOLARSHIPS:
        steps = smallest_change(profile, s)
        if steps:
            shown += 1
            st.markdown(f"**{s['name']}**: " + " ".join(steps))
    if not shown:
        st.info("Nothing to improve here. Either you are eligible, or the gap is something sliders cannot change (like category).")

# Scoring
elif page == "🧠 Scoring":
    st.markdown("<div class='page-head'><div class='eyebrow'>TRANSPARENCY</div><h2>How ScholarAI scores matches</h2><p>Understand exactly what powers the demo.</p></div>",unsafe_allow_html=True)
    t1,t2=st.tabs(["Transparent rules","Experimental ML"])
    with t1:
        st.markdown("Every scholarship has three **must-pass rules**: income, marks and group (category, gender, disability, domicile or minority).\n\n| Result | Meaning |\n|---|---|\n| ✅ Eligible | All three rules pass |\n| 🟡 Borderline | No rule clearly fails, but income is up to 10% over the limit, or marks are up to 3 points short |\n| ❌ Not eligible | At least one rule clearly fails. The group rule is strict: no near-misses. |\n\nThe ranking score (0-100) only orders scholarships *inside* a verdict. It can never turn a ❌ into a ✅.")
        st.info("This is a demonstration of explainable rules using sample data, not an official eligibility decision. Always check the provider's website.")
    with t2:
        rep = model_report()
        st.markdown("**What it is:** a small logistic-regression model that gives a *rough chance of being selected* once a student is eligible, because many scholarships have far fewer awards than applicants.\n\n**What it is not:** an eligibility decision (the rules decide that) or a real-world predictor. It is trained on **synthetic data** that we generated from our own assumptions, because no real application history was available.")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Training examples", f"{rep['n_train']:,}")
        m2.metric("Test accuracy", f"{rep['accuracy']:.0%}")
        m3.metric("Baseline (majority guess)", f"{rep['baseline']:.0%}")
        m4.metric("ROC AUC", f"{rep['auc']:.2f}")
        st.markdown("**Confusion matrix** (on {:,} held-out test examples)".format(rep["n_test"]))
        st.table(pd.DataFrame(rep["confusion"], index=["Actually not selected", "Actually selected"], columns=["Predicted not selected", "Predicted selected"]))
        imp = sorted(feature_importance(), key=lambda x: x[1])
        fig = go.Figure(go.Bar(x=[v for _, v in imp], y=[n for n, _ in imp], orientation="h"))
        fig.update_layout(height=260, margin=dict(l=10, r=30, t=10, b=20), xaxis_title="Model weight (negative lowers the chance)")
        st.plotly_chart(fig, width="stretch")
        st.warning("Limits: (1) the data is synthetic, so good scores only show the model learned our assumptions; (2) it knows nothing about how many students apply to each scholarship; (3) it is capped by the rule verdict, so a failed rule always stays near zero. It would need real, historical application outcomes before anyone should rely on it.")


st.markdown("""
<div style="margin-top:3rem;padding:1rem 0;border-top:1px solid #e8eaf1;color:#7a8090;font-size:.76rem;text-align:center;">
  <b style="color:#555b70;">ScholarAI</b> · Student scholarship workspace
  <span style="margin:0 .5rem;">•</span> Demo data only
  <span style="margin:0 .5rem;">•</span> Verify current requirements with the official provider
</div>
""", unsafe_allow_html=True)

