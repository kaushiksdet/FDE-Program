# Diabetes Readmission Intervention Queue (Week 2 FDE Mini Project)

> **Learning prototype. Not clinically validated. Not for real patient-care decisions.**

An operational backend that turns historical diabetes encounter data into a prioritised care-management
workflow: **ingest → score (explainable rules) → persist → expose via API → measure against historical outcomes.**
No ML model is built on purpose; the workflow comes first.

---

## 1. Business problem, users, decision

**Problem:** The hospital is concerned about diabetes patients returning within 30 days of discharge, and the care-management team cannot manually review every discharge.

**Decision supported:** *Which recently discharged diabetes patients should the care-management team review first?*

| User | Needs | Served by |
|---|---|---|
| Care Management Team | Prioritised review queue | `/care-queue`, `/care-queue/high`, `PATCH /interventions/{id}` |
| Hospital Operations | Queue and workload visibility | `/operations/summary` |
| Clinical Leadership | Explainable rationale | `risk_rationale` on every queue item / encounter |
| Finance / Transformation | Outcome and value signals | `/operations/readmission-analysis`, `/management/dashboard` |

## 2. FDE discovery (before coding)

| What the dataset tells us | What we do NOT know | MVP hypothesis |
|---|---|---|
| 101,766 historical encounters (71,518 distinct patients) | Which readmissions were preventable? | Prior utilisation may help prioritise follow-up |
| 11,357 (11.16%) were readmitted `<30` days | Cost of a readmission? | Care-management capacity is limited |
| Prior inpatient / ED / outpatient utilisation per patient | Current discharge workflow? | A risk queue beats reviewing everyone |
| Treatment attributes (stay length, medications, labs) | Cost of an intervention? | Rules are acceptable for an explainable MVP |
| Historical outcome (`readmitted`) | Clinical validity of the rules? | Historical outcomes can evaluate the rule *after* scoring |

## 3. Assumptions

- Scoring weights are the assignment's learning assumptions (below), not clinical recommendations.
- Each **encounter** is the unit of work (the dataset has multiple encounters per patient; `distinct_patients` is reported alongside).
- Only `<30` counts as "readmitted"; `>30` and `NO` are treated as not readmitted within 30 days.
- Missing utilisation counts would be set to 0 (none were missing in the 12 fields used); `?` is treated as null.
- Intervention workflow only moves **forward** (`PENDING_REVIEW → ASSIGNED → CONTACTED → FOLLOW_UP_SCHEDULED → CLOSED`); steps may be skipped (as in the assignment's example), but not reversed, and `CLOSED` cannot be reopened.
- The data is treated as if every row were a "recent discharge". In the real world the queue would be fed continuously.

## 4. Scoring rule (in `service.py`)

| Condition | Points |
|---|---|
| `number_inpatient >= 3` | +3 |
| `number_emergency >= 2` | +2 |
| `number_outpatient >= 3` | +1 |
| `time_in_hospital >= 7` | +1 |
| `num_medications >= 20` | +1 |

`0–2 = LOW`, `3–4 = MEDIUM`, `5+ = HIGH`.

**No data leakage:** `calculate_risk()` takes only the five feature fields as arguments; `readmitted` is never passed to it. `readmitted` is read only in the `readmission_*` evaluation queries *after* scoring. The care-queue API responses deliberately omit it.

## 5. Architecture

```
diabetic_data.csv -> data_loader.py -> PostgreSQL <- repository.py <- service.py <- main.py (FastAPI) <- Swagger / consumers
```

| File | Responsibility |
|---|---|
| `database.py` | DB config (env vars) + connection context manager only |
| `repository.py` | **All SQL**, fully parameterised (`%s` bind params; dynamic fragments use only hard-coded column names) |
| `service.py` | Risk rules, rationale, workflow rules, metric assembly |
| `models.py` | Pydantic request/response models and enums |
| `main.py` | Routes, validation, HTTP error mapping (404 / 409 / 422) |
| `data_loader.py` | Repeatable CSV cleanup → bulk `COPY` → upsert → create interventions |
| `schema.sql` / `seed_or_setup.sql` | Tables, constraints, indexes / one-time DB creation |

**Tables:** `patient_encounters` (12 source fields + `risk_score`, `risk_level`) and `care_interventions` (`intervention_id`, `encounter_id` UNIQUE FK, `status` with CHECK constraint, `assigned_to`, `notes`, `created_at`, `updated_at`).

**Loader behaviour:** reads only the 12 needed columns, converts `?` to null, drops rows missing key fields, de-duplicates on `encounter_id`, validates `readmitted ∈ {<30,>30,NO}`, bulk-loads via `COPY` to a staging table and upserts (re-running is safe and **preserves existing intervention progress**). It then creates a `PENDING_REVIEW` intervention for every MEDIUM/HIGH encounter. Full load ≈ 2 seconds.

## 6. API list

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/encounters` | List encounters (paginated; filters `risk_level`, `min_risk_score`) |
| GET | `/encounters/{encounter_id}` | One encounter + risk rationale + intervention (404 if missing) |
| GET | `/care-queue` | MEDIUM + HIGH queue, highest score first (filters `min_risk_score`, `status`; paginated) |
| GET | `/care-queue/high` | HIGH only |
| PATCH | `/interventions/{encounter_id}` | Update `status` / `assigned_to` / `notes` |
| GET | `/operations/summary` | Counts by risk level and intervention status |
| GET | `/operations/readmission-analysis` | Risk groups vs historical `<30` outcomes |
| GET | `/management/dashboard` | Executive summary (lift, capture rate, workflow progress, age bands) |
| GET | `/care-queue-export.csv` | *(stretch)* CSV export of the queue |

Errors: `404` unknown encounter ID · `409` encounter is LOW risk (not in queue), backwards/reopen transition, or empty PATCH body · `422` invalid status / bad parameter types.
Stretch goals included: pagination, min-score filter, age-band summary, CSV export.

## 7. Run instructions

```bash
# 1. PostgreSQL running locally. Create the database:
psql -U postgres -f seed_or_setup.sql          # or: createdb readmission_db

# 2. Python environment
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # edit DB_PASSWORD etc.

# 3. Put the dataset at data/diabetic_data.csv, then load (idempotent)
python data_loader.py

# 4. Start the API
uvicorn main:app --reload
# Swagger UI: http://127.0.0.1:8000/docs
```

Example update:
```bash
curl -X PATCH http://127.0.0.1:8000/interventions/168920160 \
  -H "Content-Type: application/json" \
  -d '{"status":"CONTACTED","assigned_to":"Care Team A","notes":"Follow-up appointment scheduled"}'
```

## 8. Results (calculated from the stored data, not hard-coded)

| Risk level | Encounters | Readmitted `<30` | Rate | Lift vs 11.16% baseline |
|---|---|---|---|---|
| HIGH | 2,358 | 674 | **28.58%** | 2.56× |
| MEDIUM | 6,180 | 1,335 | 21.60% | 1.94× |
| LOW | 93,228 | 9,348 | 10.03% | 0.90× |
| **Queue (MEDIUM+HIGH)** | 8,538 (8.4% of all) | 2,009 | 23.53% | 2.11× |

Readmission rate rises monotonically-ish with score (score 0 → 9.0%, 3 → 21.2%, 5 → 27.9%, 7+ → 32.3%).

## 9. FDE reflection

**1. What business problem did you solve?**
The care team cannot review every discharge. I built the operational workflow that picks a review queue (8,538 of 101,766 encounters, ~8%), explains why each case is there, tracks the intervention lifecycle with persisted state, and measures whether the queue targets higher-risk people.

**2. Who is the primary user?**
The care-management team lead/nurse working the queue; Operations, Clinical Leadership and Finance are secondary consumers of the metrics endpoints.

**3. What decision does your application improve?**
Which discharged patients to contact first, and how to allocate limited capacity: work `/care-queue/high` first, then MEDIUM, by descending score.

**4. What did the dataset prove?**
Historically, the rule identifies a population with materially higher `<30` readmission: HIGH is 28.6% vs an 11.2% baseline (2.6×) and LOW is below baseline (10.0%). It did **not** prove the rule is good enough alone: the queue captures only ~17.7% of all `<30` readmissions, so most readmissions come from LOW-scored encounters. It is a useful prioritiser, not a detector. It also did not prove that contacting these patients *prevents* readmission (no intervention data in the set).

**5. What assumptions did you make?**
See §3: weights are learning assumptions; encounter-level unit; `<30` only counts as readmitted; forward-only workflow; all rows treated as recent discharges; missing counts → 0.

**6. What must the hospital validate before this could become a real product?**
- Clinical validity and fairness of the weights (and by age/race/subgroup), with clinician sign-off.
- Preventability of readmissions, cost of a readmission vs cost/capacity of an intervention (ROI is unknown, so the dashboard intentionally shows no money figure).
- **Discharge dispositions that cannot lead to readmission:** 2,423 encounters here have disposition codes 11/13/14/19/20/21 (expired / hospice), with a 1.77% `<30` rate. A production queue should exclude them; I kept them to match the assignment's simple scope and flag it here.
- Same-patient repeated encounters (71,518 patients vs 101,766 encounters) and how the queue de-duplicates them.
- Data freshness/integration with the real discharge workflow, security/PHI controls, audit trail (an intervention-history table would replace overwrite-in-place), and a prospective pilot with a control group.

**7. Rules, traditional ML, LLM, or another approach next, and why?**
Keep the rules as the transparent baseline and next try a **traditional ML model** (e.g. regularised logistic regression / gradient boosting on this tabular data) trained on patient-grouped, time-aware splits and judged against the rule on the same metric (capture of `<30` readmissions at fixed queue capacity). Tabular structured data suits it, and calibrated scores plus SHAP-style explanations keep explainability. An LLM is not the right tool for scoring, but could later summarise case notes or draft outreach, with human review. Rules stay as the fallback and benchmark.

## 10. Submission checklist

- [x] Source: `main.py models.py service.py repository.py database.py data_loader.py schema.sql seed_or_setup.sql`
- [x] `README.md`, `requirements.txt`, `.env.example`, `data/` dataset
- [ ] Swagger screenshot (open `/docs`, expand the endpoints, screenshot)
- [ ] PostgreSQL screenshot (`SELECT COUNT(*) FROM patient_encounters;` and `SELECT * FROM care_interventions LIMIT 10;`)
- [ ] 3–5 minute demo video (script: problem → run loader → `/care-queue/high` → PATCH → restart server and show status persisted → `/operations/readmission-analysis` → reflection)

*Learning use only, not for clinical decision-making.*
