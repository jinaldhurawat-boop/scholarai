# ScholarAI: Scholarship Eligibility Predictor

ScholarAI tells a student **which scholarships they are eligible for, why or why not, and what would change the answer**. It is built with Python and Streamlit.

> **Read this first.** ScholarAI is a student project, not an official government service. The scholarship data was researched on 4 October 2026 from public sources and only some entries are checked against official pages (see *Data status*). Always confirm eligibility and deadlines on the provider's website before applying.

## What it does

| Feature | What the student gets |
|---|---|
| **Profile form** | Name, course, category, income, marks, gender, home state, field of study, minority / disability / first-generation status |
| **Honest verdicts** | Every scholarship is marked ✅ Eligible, 🟡 Borderline or ❌ Not eligible, with a rule-by-rule explanation |
| **What-if simulator** | Move income and marks sliders to see which verdicts change, plus the smallest change needed to qualify |
| **Discover** | Search and filter all scholarships, save favourites, compare up to 4 side by side |
| **Application tracker** | Move saved scholarships through Interested, Preparing, Ready to submit and Submitted, go back a step, or remove |
| **Documents and deadlines** | Document checklist for your best matches, and deadlines sorted by urgency |
| **Report export** | Download your results as a text file |
| **Experimental ML estimate** | A rough "chance of being selected" for eligible students (see below) |

## How eligibility works

Each scholarship has **must-pass rules**: income limit, minimum marks, the group it is for (category, gender, disability, domicile or minority), and sometimes extras such as field of study, first-generation status or home state.

- ✅ **Eligible**: every rule passes.
- 🟡 **Borderline**: nothing clearly fails, but income is up to 10% over the limit, or marks are up to 3 points short.
- ❌ **Not eligible**: at least one rule clearly fails. Group rules are strict, with no near-misses.

A 0-100 **ranking score** only orders scholarships inside a verdict. It can never turn a ❌ into a ✅. The rules live in `eligibility.py` and are covered by unit tests.

## The ML part (experimental, and honest about it)

The rules decide eligibility. The ML model only estimates a **rough chance of being selected** once a student is eligible, because many scholarships have far fewer awards than applicants.

- Model: logistic regression on 4 numbers (income vs limit, marks above minimum, rules clearly failed, rules nearly missed).
- Training data: **synthetic**, generated from stated assumptions, because no real application history was available.
- Evaluation (80/20 split, shown on the *Scoring* page): about 87% accuracy against a 74% majority-guess baseline, AUC about 0.94.
- What that means: the model learned our assumptions. It says nothing about real selection outcomes, and it knows nothing about how many students apply.
- Safety: the model is capped by the rule verdict, so a failed rule always stays near zero.

## Data status

The scholarships are in `scholarships.json`. Each entry has a source link, notes and a `last_verified` date.

| Status | Entries |
|---|---|
| **Rules checked against an official source** (4 Oct 2026) | Reliance Foundation Undergraduate, PM-USP CSSS, Post-Matric for ST, Rajarshi Shahu Maharaj (Maharashtra EBC) |
| **Unverified** (secondary sources only) | Post-Matric for SC, PM YASASVI (OBC), AICTE Pragati, Post-Matric for Disabilities, Post-Matric for Minorities, Merit-cum-Means for Minorities, Infosys STEM Stars, Tamil Nadu First Graduate |

The app labels each one on screen. Deadlines for CSSS, Maharashtra, Infosys and Tamil Nadu are **sample dates**.

## Known limitations

These real-world rules are **not** modelled, so the app can show ✅ where a student could still be rejected:

- **Percentile rules** (CSSS needs the 80th percentile of the Class 12 board; the app approximates it with 80% marks)
- **First-year-only schemes** (Reliance, Pragati, Infosys)
- **Professional or technical course restrictions** (Merit-cum-Means for Minorities)
- **CAP admission and the two-children limit** (Maharashtra EBC)
- **Pragati's "technical course"** is approximated as the STEM field
- **Income limits change.** The SC post-matric limit is 2.5 lakh now, and the government has said it plans to raise it to 4.5 lakh.
- Only 12 scholarships are included, mostly central schemes plus one Maharashtra, one Tamil Nadu and two private ones
- Data is stored in a single local JSON file with no login, so it is meant for one user on one computer

## Run it

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Run the tests (26 tests: rule engine, scholarship data, ML model):

```bash
python -m unittest discover -v
```

## Project structure

```
app.py                  Streamlit pages and layout
eligibility.py          Rule engine: verdicts, rule-by-rule checks, smallest change
ml_model.py             Experimental selection-chance model and its evaluation
scoring.py              Small facade used by app.py
scholarship_data.py     Loads scholarships.json, dropdown lists, document checklist
scholarships.json       The scholarship data (edit this, not the code)
storage.py              Saves the profile, saved scholarships and tracker to data/
styles.py               CSS
tests/                  Unit tests
```

## Updating the data

Edit `scholarships.json`. For each scholarship you check on an official site, set `source_url`, a real `"deadline": "YYYY-MM-DD"` and `last_verified`. The "unverified" label disappears automatically. Run the tests afterwards.

## Future work

- Verify the remaining 8 entries on official portals and add real deadlines
- Model percentile rules, first-year-only, course type and per-family limits
- Add more scholarships and state schemes, with a field for each state's rules
- Replace the synthetic ML data with real historical application outcomes, if they can be obtained
- Per-user accounts and storage
