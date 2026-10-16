from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
InterventionStatus = Literal[
    "PENDING_REVIEW",
    "ASSIGNED",
    "CONTACTED",
    "FOLLOW_UP_SCHEDULED",
    "CLOSED",
]


class Encounter(BaseModel):
    """Represents a single patient hospital encounter with calculated risk score and level."""
    encounter_id: int
    patient_nbr: int
    age: str
    time_in_hospital: int
    number_inpatient: int
    number_emergency: int
    number_outpatient: int
    num_medications: int
    num_lab_procedures: int
    discharge_disposition_id: int
    admission_type_id: int
    readmitted: str
    risk_score: int
    risk_level: RiskLevel


class Intervention(BaseModel):
    """Represents a care intervention record for high or medium risk encounters."""
    intervention_id: int
    encounter_id: int
    status: InterventionStatus
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CareQueueItem(Encounter):
    """Combines patient encounter details with its corresponding care intervention status."""
    intervention_id: int
    status: InterventionStatus
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class InterventionUpdate(BaseModel):
    """Request payload for updating intervention status, assignment, or notes."""
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class OperationsSummary(BaseModel):
    """Summary metrics of patient encounter risk tiers and intervention queue progress."""
    total_encounters: int
    high_risk: int
    medium_risk: int
    low_risk: int
    pending_interventions: int
    completed_interventions: int


class RiskGroupReadmissionAnalysis(BaseModel):
    """Readmission metrics for a specific risk level group (e.g., HIGH, MEDIUM, LOW)."""
    risk_level: RiskLevel
    total_patients: int
    readmitted_under_30_days: int
    readmission_rate: float


class ReadmissionAnalysis(BaseModel):
    """Aggregated 30-day readmission analysis overall and broken down by risk group."""
    total_encounters: int
    readmitted_under_30_days: int
    readmission_rate: float
    risk_groups: List[RiskGroupReadmissionAnalysis]


class ManagementDashboard(BaseModel):
    """Executive dashboard metrics summarizing care queue volume and high-risk readmission rate."""
    total_encounters: int
    care_queue_size: int
    high_risk_queue: int
    medium_risk_queue: int
    pending_interventions: int
    completed_interventions: int
    high_risk_readmission_rate: float
