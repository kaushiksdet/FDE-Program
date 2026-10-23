from typing import List, Optional

import psycopg2
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

import service
from models import (
    CareQueueItem,
    Encounter,
    EncounterCreate,
    EncounterCreated,
    Intervention,
    InterventionUpdate,
    ManagementDashboard,
    OperationsSummary,
    PatientSearchResult,
    ReadmissionAnalysis,
    RiskLevel,
)


app = FastAPI(
    title="Diabetes Readmission Intervention Queue",
    description=(
        "Operational MVP for prioritizing diabetes readmission care-management review. "
        "Learning prototype only - not for clinical decision-making."
    ),
    version="1.1.0",
)


@app.exception_handler(psycopg2.OperationalError)
def database_unavailable_handler(request: Request, error: psycopg2.OperationalError):
    """
    Return 503 instead of a raw 500 when PostgreSQL is unreachable.
    """
    return JSONResponse(
        status_code=503,
        content={"detail": "Database is unavailable. Check DATABASE_URL and that PostgreSQL is running."},
    )


@app.get("/")
def health_check():
    """
    Health check endpoint: returns service running status and docs location.
    """
    return {
        "service": "Diabetes Readmission Intervention Queue",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/encounters", response_model=List[Encounter])
def list_encounters(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    Retrieve a paginated list of patient encounters.
    """
    return service.list_encounters(limit=limit, offset=offset)


@app.post("/encounters", response_model=EncounterCreated, status_code=201)
def create_encounter(payload: EncounterCreate):
    """
    Add a new patient encounter. The server assigns encounter_id, calculates the risk score
    and level, and adds the encounter to the care queue when it is MEDIUM/HIGH risk.
    """
    return service.create_encounter(payload.model_dump())


@app.get("/encounters/search", response_model=List[PatientSearchResult])
def search_encounters(
    patient_nbr: Optional[int] = Query(default=None, gt=0),
    risk_level: Optional[RiskLevel] = Query(default=None),
    risk_score: Optional[int] = Query(default=None, ge=0, le=8),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    Search encounters by patient number and/or risk level and/or exact risk score,
    with the care intervention status for queued encounters. Highest risk first.
    """
    try:
        return service.search_encounters(
            patient_nbr=patient_nbr,
            risk_level=risk_level,
            risk_score=risk_score,
            limit=limit,
            offset=offset,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/encounters/{encounter_id}", response_model=Encounter)
def get_encounter(encounter_id: int):
    """
    Fetch a single patient encounter by its encounter ID (returns 404 if not found).
    """
    try:
        return service.get_encounter(encounter_id)
    except service.EncounterNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/care-queue", response_model=List[CareQueueItem])
def get_care_queue(
    min_risk_score: Optional[int] = Query(default=None, ge=0, le=8),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    Retrieve the prioritized care queue (HIGH and MEDIUM risk), highest score first,
    with an optional minimum risk score filter.
    """
    return service.get_care_queue(
        min_risk_score=min_risk_score,
        limit=limit,
        offset=offset,
    )


@app.get("/care-queue/high", response_model=List[CareQueueItem])
def get_high_risk_care_queue(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    Retrieve care queue records filtered exclusively for high-risk patient encounters.
    """
    return service.get_care_queue(
        high_only=True,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/interventions/{encounter_id}",
    response_model=Intervention,
    responses={
        404: {"description": "Encounter does not exist"},
        409: {"description": "Encounter exists but is not in the care queue"},
    },
)
def get_intervention(encounter_id: int):
    """
    Fetch the care intervention (status, assignee, notes) for an encounter.
    """
    try:
        return service.get_intervention(encounter_id)
    except service.EncounterNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except service.NotInCareQueueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.patch(
    "/interventions/{encounter_id}",
    response_model=Intervention,
    responses={
        404: {"description": "Encounter does not exist"},
        409: {"description": "Encounter exists but is not in the care queue"},
    },
)
def update_intervention(encounter_id: int, payload: InterventionUpdate):
    """
    Update workflow status, assignee, or notes for an intervention by encounter ID.
    """
    update_data = payload.model_dump(exclude_unset=True)

    try:
        return service.update_intervention(
            encounter_id=encounter_id,
            status=update_data.get("status"),
            assigned_to=update_data.get("assigned_to"),
            notes=update_data.get("notes"),
        )
    except service.EncounterNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except service.NotInCareQueueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/operations/summary", response_model=OperationsSummary)
def get_operations_summary():
    """
    Retrieve risk-tier counts and care-queue workload (pending / in progress / completed).
    """
    return service.get_operations_summary()


@app.get("/operations/readmission-analysis", response_model=ReadmissionAnalysis)
def get_readmission_analysis():
    """
    Compare the prioritization rule against historical <30-day readmissions:
    per risk level, queue vs non-queue, and lift over the overall baseline.
    """
    return service.get_readmission_analysis()


@app.get("/management/dashboard", response_model=ManagementDashboard)
def get_management_dashboard():
    """
    Retrieve executive metrics: queue volume, workflow progress, and targeting effectiveness.
    """
    return service.get_management_dashboard()
