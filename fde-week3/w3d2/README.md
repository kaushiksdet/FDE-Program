# Diabetes Readmission Intervention Queue

> **Learning prototype only.** This is not a clinically validated scoring system and must not be used for real patient care decisions.

## Project Overview

This project is a Forward Deployed Engineer mini project for an enterprise healthcare scenario. The application converts historical diabetes hospital encounter data into an operational care-management queue.

The goal is not to build a clinical prediction model. The goal is to build a backend workflow that helps a hospital prioritize which recently discharged diabetes patients should be reviewed first by the care-management team, and to measure whether that prioritization lines up with historical outcomes.

## What changed in this version

This version adds the complete end-to-end workflow for the hospital operations use case:

- a cleaned and scored encounter ingestion pipeline from the diabetes CSV
- a PostgreSQL-backed API with queue prioritization and workflow tracking
- a React + TypeScript front end for adding encounters, searching patients, reviewing the high-risk queue, and updating case status
- operational analytics for risk distribution, queue workload, and historical readmission lift
- a Postman collection and demo script for validating the API and walking through the user flow

## Business Problem

Hospitals often have more discharged patients than a care-management team can manually review. For diabetes patients, early readmission within 30 days is an important operational and financial concern.

This application helps the hospital identify patients who should be reviewed first by applying a simple, explainable risk rule to historical encounter data.

**Primary business decision:** Which recently discharged diabetes patients should the care-management team review first?

## Primary Users

| User | What they need | Business outcome |
| --- | --- | --- |
| Care Management Team (primary) | Prioritized review queue | Focus limited capacity on higher-risk cases |
| Hospital Operations | Queue and workload visibility | Understand intervention volume and backlog |
| Clinical Leadership | Explainable rationale | Review whether prioritization is operationally sensible |
| Finance / Transformation | Outcome and value signals | Assess whether the intervention is worth scaling |

## FDE Discovery Before Coding

| What the dataset tells us | What we do NOT know | MVP hypothesis |
| --- | --- | --- |
| ~101,766 historical diabetes encounters for ~71,518 patients | Which readmissions were preventable | Prior utilization (inpatient / emergency / outpatient visits) may help prioritize follow-up |
| Whether each encounter was readmitted `<30` days, `>30` days, or `NO` | The cost of a readmission | Care-management capacity is limited, so not every patient can be reviewed |
| Prior healthcare utilization in the year before the encounter | The hospital's current discharge and follow-up workflow | A risk-ordered queue is a better use of capacity than reviewing everyone equally |
| Operational / treatment attributes (length of stay, medications, lab procedures, admission type, discharge disposition) | The cost and capacity of an intervention (calls, visits) | A rule-based score is acceptable for an explainable MVP |
| Discharge disposition, including patients who expired or went to hospice | Whether the scoring rules are clinically valid | Historical outcomes can be used to evaluate the rule after scoring, without leaking into the score |

## Dataset Fields Used

The application uses a focused subset of `backend/data/diabetic_data.csv`:

`encounter_id`, `patient_nbr`, `age`, `time_in_hospital`, `number_inpatient`, `number_emergency`, `number_outpatient`, `num_medications`, `num_lab_procedures`, `discharge_disposition_id`, `admission_type_id`, `readmitted`

**Data leakage rule:** `readmitted` is the historical outcome. It is stored for evaluation only and is never used to calculate `risk_score` (see `calculate_risk_score` in `backend/service.py`).

### Data cleanup

`backend/data_loader.py` reads only the required columns, treats `?` and blanks as missing, and drops (rather than imputes) rows that cannot be scored reliably. Each load prints a cleanup report:

| Check | Action |
| --- | --- |
| Missing value in any required field | Drop row |
| Non-numeric value in a numeric field | Drop row |
| Negative visit / medication / lab counts | Drop row |
| `readmitted` not one of `NO`, `>30`, `<30` | Drop row |
| Duplicate `encounter_id` | Keep first |

On the provided dataset all 101,766 rows passed. The loader is re-runnable: encounters are upserted and existing intervention work is preserved.

## Risk Scoring Rule

| Condition | Points |
| --- | ---: |
| `number_inpatient >= 3` | +3 |
| `number_emergency >= 2` | +2 |
| `number_outpatient >= 3` | +1 |
| `time_in_hospital >= 7` | +1 |
| `num_medications >= 20` | +1 |

| Score | Risk level |
| ---: | --- |
| 0-2 | LOW |
| 3-4 | MEDIUM |
| 5+ | HIGH |

These weights are learning assumptions, not clinical recommendations.

### Care queue eligibility

An encounter enters the care queue (`care_interventions`, status `PENDING_REVIEW`) when:

1. Its risk level is **MEDIUM** or **HIGH**, and
2. Its `discharge_disposition_id` is **not** 11, 19, 20 or 21 (expired / hospice death). These patients cannot receive post-discharge outreach, so queuing them would waste care-team capacity. 188 MEDIUM/HIGH encounters are excluded for this reason, and the count is reported as `excluded_from_queue`.

The queue is ordered by `risk_score` (highest first), then by prior inpatient and emergency visits.

### Intervention workflow

```text
PENDING_REVIEW -> ASSIGNED -> CONTACTED -> FOLLOW_UP_SCHEDULED -> CLOSED
```

Metrics group these statuses as **pending** (`PENDING_REVIEW`), **in progress** (`ASSIGNED`, `CONTACTED`, `FOLLOW_UP_SCHEDULED`) and **completed** (`CLOSED`).

## Architecture

```text
Healthcare CSV Dataset
        |
        v
backend/data_loader.py  (clean -> score -> upsert -> sync queue)
        |
        v
PostgreSQL
        ^
        |
backend/repository.py   (parameterized SQL only)
        ^
        |
backend/service.py      (risk rules, queue eligibility, workflow validation, metrics)
        ^
        |
backend/main.py         (FastAPI routes, HTTP errors)
        ^
        |
Swagger / API Consumer / frontend (React UI, via Vite /api proxy)
```

| File | Responsibility |
| --- | --- |
| `backend/database.py` | PostgreSQL connection configuration (reads the repository-root `.env`) |
| `backend/schema.sql` | Tables, constraints, indexes, `updated_at` trigger |
| `backend/seed_or_setup.sql` | Creates the database and applies `schema.sql` in one step |
| `backend/data_loader.py` | CSV ingestion, cleanup report, scoring, queue sync |
| `backend/service.py` | Business rules: scoring, risk levels, queue eligibility, status validation, rates and lift |
| `backend/repository.py` | SQL queries and persistence only; every user value is passed as a parameter |
| `backend/models.py` | Pydantic request and response models |
| `backend/main.py` | FastAPI routes and HTTP error mapping |
| `backend/requirements.txt` | Python API and data-loader dependencies |
| `frontend/` | React + TypeScript UI: add encounter, patient search, high-risk queue, status tracking |
| `postman/` | API test collection and environment for local validation |
| `docs/DEMO_SCRIPT.md` | Demo walkthrough for the business case and product story |

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/encounters?limit=&offset=` | List encounters (paginated) |
| POST | `/encounters` | Add an encounter (Add Patient Encounter form); risk is scored and MEDIUM/HIGH encounters are queued (201) |
| GET | `/encounters/search?patient_nbr=&risk_level=&risk_score=` | Search by any combination of patient number, risk level and exact risk score; includes care status |
| GET | `/encounters/{encounter_id}` | Get one encounter (404 if missing) |
| GET | `/care-queue?min_risk_score=&limit=&offset=` | MEDIUM + HIGH queue, highest score first |
| GET | `/care-queue/high?limit=&offset=` | HIGH risk queue only |
| GET | `/interventions/{encounter_id}` | Get an encounter's care status / owner / notes (404 / 409 like PATCH) |
| PATCH | `/interventions/{encounter_id}` | Update workflow status / owner / notes |
| GET | `/operations/summary` | Risk tiers and queue workload |
| GET | `/operations/readmission-analysis` | Compare prioritization against historical `<30` outcomes |
| GET | `/management/dashboard` | Executive summary metrics |

### Error responses

| Situation | Status |
| --- | --- |
| Encounter ID does not exist | `404 Not Found` |
| Encounter exists but is not in the queue (LOW risk, or expired / hospice) | `409 Conflict`, with the reason |
| Invalid status value or field type | `422 Unprocessable Entity`, with the allowed values |
| PostgreSQL unreachable | `503 Service Unavailable` |

### Example intervention update

```http
PATCH /interventions/168920160
Content-Type: application/json

{
  "status": "CONTACTED",
  "assigned_to": "Care Team A",
  "notes": "Follow-up appointment scheduled"
}
```

## Results on the Provided Dataset

All numbers below are calculated by the API from the stored data (`/operations/summary`, `/operations/readmission-analysis`).

| Risk level | Encounters | Readmitted `<30` | Rate | Times baseline |
| --- | ---: | ---: | ---: | ---: |
| HIGH | 2,358 | 674 | 28.58% | 2.56x |
| MEDIUM | 6,180 | 1,335 | 21.60% | 1.94x |
| LOW | 93,228 | 9,348 | 10.03% | 0.90x |
| **All encounters (baseline)** | **101,766** | **11,357** | **11.16%** | 1.00x |

| Population | Encounters | Rate |
| --- | ---: | ---: |
| In care queue | 8,350 (8.2% of encounters) | 24.06% |
| Not in queue | 93,416 | 10.01% |

The queue covers **8.2% of encounters but captures 17.7% of all `<30`-day readmissions**.

## Setup Instructions (macOS / Linux)

1. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```

2. Configure the database connection:

   ```bash
   cp .env.example .env
   # edit .env and set DATABASE_URL=postgresql://postgres:<password>@localhost:5432/fde_db
   ```

3. Create the database and tables (run from the project root):

   ```bash
   psql -U postgres -f backend/seed_or_setup.sql
   ```

4. Check the connection, then load the dataset:

   ```bash
   python backend/database.py
   python backend/data_loader.py
   ```

5. Start the API and open Swagger at <http://127.0.0.1:8000/docs>:

   ```bash
   cd backend
   uvicorn main:app --reload
   ```

6. In a second terminal, start the UI and open <http://localhost:5173>:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   The UI calls `/api/...`, which Vite proxies to `http://localhost:8000`. Use `API_URL=http://host:port npm run dev` if the API runs elsewhere.

Useful verification queries are listed at the bottom of `backend/seed_or_setup.sql`.

## Screenshots

**Swagger: key endpoints**

![Swagger endpoints](docs/screenshots/swagger_endpoints.png)

**PostgreSQL: loaded records** (queries in [`docs/screenshots/verify_queries.sql`](docs/screenshots/verify_queries.sql))

![PostgreSQL loaded records](docs/screenshots/postgresql_loaded_records.png)

## FDE Reflection

### 7. What business problem did you solve?

I solved the problem of limited care-management capacity. The hospital cannot manually review every discharged diabetes patient, so the application creates a prioritized review queue based on simple operational risk factors.

The solution turns historical encounter data into an actionable workflow: load and clean patient encounters, calculate risk, create a care queue, track interventions, and measure whether the prioritization aligns with historical readmission outcomes.

### 8. Who is the primary user?

The primary user is the care-management team. They need a practical queue that tells them which patients to review first.

Secondary users include hospital operations leaders, clinical leadership, and finance or transformation teams who need visibility into workload, outcomes, and possible value.

### 9. What decision does your application improve?

The application improves the decision of which recently discharged diabetes patients should receive care-management attention first.

Instead of reviewing patients randomly or equally, the team works a queue of about 8% of encounters, ordered by risk score, and skips patients who cannot be contacted after discharge.

### 10. What did the dataset prove?

Within this historical data, the simple rule separates risk groups clearly:

- HIGH risk encounters were readmitted within 30 days at **28.58%**, about **2.6 times** the overall baseline of **11.16%**.
- MEDIUM risk encounters were readmitted at **21.60%** (about 1.9 times baseline).
- LOW risk encounters were readmitted at **10.03%**, slightly below baseline.
- The queue holds **8.2%** of encounters but accounts for **17.7%** of all `<30`-day readmissions.

The dataset does **not** prove clinical causality or preventability. It also shows the rule's limit: most `<30` readmissions (about 82%) come from LOW risk encounters, because that group is so large. The queue concentrates risk but does not catch most readmissions.

### 11. What assumptions did you make?

- Prior inpatient, emergency, and outpatient utilization are useful operational signals for follow-up priority.
- Longer hospital stays and a higher number of medications may indicate more complex cases.
- A simple rule-based approach is acceptable for an MVP because it is explainable, easy to inspect, and easy for business and clinical stakeholders to challenge.
- Care-management capacity is limited, so a prioritized queue is more useful than reviewing every patient.
- Patients discharged as expired or to hospice (disposition 11, 19, 20, 21) should not be queued for outreach.
- Each encounter is treated independently; a patient with several encounters can appear in the queue more than once.
- Rows with missing or invalid key fields are dropped rather than imputed.

### 12. What must the hospital validate before this could become a real product?

- Whether the scoring rule is clinically appropriate and operationally useful.
- Which readmissions were preventable, what interventions are available, how much each costs, and how many cases the team can handle per week.
- Whether the queue improves outcomes compared with the current workflow, ideally through a controlled pilot.
- Data quality and freshness from live discharge feeds rather than a historical extract.
- Privacy and security controls (authentication, role-based access, audit logging, HIPAA compliance), workflow ownership, and integration with real discharge and care-management systems.

### 13. Would you use rules, traditional ML, LLM, or another approach next - and why?

For the MVP, I would use rules because they are transparent, fast to implement, and easy for stakeholders to review.

Next, I would compare the rule-based approach with a traditional machine learning model such as logistic regression or gradient boosting, evaluated the same way (rate and lift per queue size). Traditional ML could identify more complex patterns and catch more of the readmissions currently in the LOW group, but it should only be introduced after the hospital agrees on the workflow, outcome definition, intervention process, and evaluation method.

I would not use an LLM as the primary scoring engine for this use case. An LLM may help summarize notes or explain queue rationale, but patient prioritization should rely on validated, measurable, and auditable logic.

## Important Note

This application is a learning prototype. It is not clinically validated and must not be used for real patient care decisions.
