from typing import Any, Mapping


REQUIRED_DATASET_COLUMNS = [
    "encounter_id",
    "patient_nbr",
    "age",
    "time_in_hospital",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "num_medications",
    "num_lab_procedures",
    "discharge_disposition_id",
    "admission_type_id",
    "readmitted",
]

VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}

VALID_INTERVENTION_STATUSES = {
    "PENDING_REVIEW",
    "ASSIGNED",
    "CONTACTED",
    "FOLLOW_UP_SCHEDULED",
    "CLOSED",
}


def calculate_risk_score(encounter: Mapping[str, Any]) -> int:
    """
    Calculate risk score from operational fields only.

    The historical readmitted outcome must not be used here.
    """
    score = 0

    if int(encounter["number_inpatient"]) >= 3:
        score += 3
    if int(encounter["number_emergency"]) >= 2:
        score += 2
    if int(encounter["number_outpatient"]) >= 3:
        score += 1
    if int(encounter["time_in_hospital"]) >= 7:
        score += 1
    if int(encounter["num_medications"]) >= 20:
        score += 1

    return score


def calculate_risk_level(risk_score: int) -> str:
    """
    Convert a numeric risk score into the assignment risk level.
    """
    if risk_score >= 5:
        return "HIGH"
    if risk_score >= 3:
        return "MEDIUM"
    return "LOW"


def score_encounter(encounter: Mapping[str, Any]) -> dict[str, Any]:
    """
    Return an encounter dictionary with risk_score and risk_level added.
    """
    scored_encounter = dict(encounter)
    risk_score = calculate_risk_score(scored_encounter)
    scored_encounter["risk_score"] = risk_score
    scored_encounter["risk_level"] = calculate_risk_level(risk_score)
    return scored_encounter


def normalize_intervention_status(status: str) -> str:
    """
    Normalize and validate a workflow status value.
    """
    normalized_status = status.strip().upper()

    if normalized_status not in VALID_INTERVENTION_STATUSES:
        allowed_statuses = ", ".join(sorted(VALID_INTERVENTION_STATUSES))
        raise ValueError(f"Invalid intervention status. Allowed values: {allowed_statuses}")

    return normalized_status


def calculate_rate(numerator: int, denominator: int) -> float:
    """
    Calculate a percentage rate rounded to two decimal places.
    """
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)
