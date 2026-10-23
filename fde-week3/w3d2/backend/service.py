"""
Business layer: risk scoring, care-queue eligibility, workflow validation, and metric
calculations. Routes in main.py call this module; this module calls repository.py for data.
"""

from typing import Any, Mapping, Optional

import repository


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

VALID_READMITTED_VALUES = {"NO", ">30", "<30"}

VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
QUEUE_RISK_LEVELS = ["HIGH", "MEDIUM"]

# Discharge dispositions where post-discharge outreach is not possible
# (IDS_mapping.csv: 11 = Expired, 19/20/21 = Expired / hospice-related death).
EXCLUDED_DISCHARGE_DISPOSITIONS = [11, 19, 20, 21]

VALID_INTERVENTION_STATUSES = {
    "PENDING_REVIEW",
    "ASSIGNED",
    "CONTACTED",
    "FOLLOW_UP_SCHEDULED",
    "CLOSED",
}
IN_PROGRESS_STATUSES = {"ASSIGNED", "CONTACTED", "FOLLOW_UP_SCHEDULED"}


class EncounterNotFoundError(Exception):
    """Raised when an encounter ID does not exist."""


class NotInCareQueueError(Exception):
    """Raised when an encounter exists but is not eligible for the care queue."""


# ---------------------------------------------------------------------------
# Risk scoring (never uses the historical `readmitted` outcome)
# ---------------------------------------------------------------------------

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


def sync_care_queue() -> dict[str, int]:
    """
    Bring care_interventions in line with the eligibility rule: an encounter is queued if it is
    MEDIUM/HIGH risk and was not discharged as expired / hospice death. Adds newly eligible
    encounters and drops ineligible entries that no one has started working.
    """
    removed = repository.delete_ineligible_untouched_interventions(
        QUEUE_RISK_LEVELS, EXCLUDED_DISCHARGE_DISPOSITIONS
    )
    created = repository.create_care_interventions(
        QUEUE_RISK_LEVELS, EXCLUDED_DISCHARGE_DISPOSITIONS
    )
    return {"created": created, "removed": removed}


# ---------------------------------------------------------------------------
# Encounters and care queue
# ---------------------------------------------------------------------------

def list_encounters(limit: int, offset: int) -> list[dict[str, Any]]:
    return repository.get_encounters(limit=limit, offset=offset)


def get_encounter(encounter_id: int) -> dict[str, Any]:
    encounter = repository.get_encounter_by_id(encounter_id)
    if encounter is None:
        raise EncounterNotFoundError(f"Encounter {encounter_id} was not found.")
    return encounter


def is_queue_eligible(encounter: Mapping[str, Any]) -> bool:
    """
    Same rule as sync_care_queue: MEDIUM/HIGH risk and not discharged as expired / hospice death.
    """
    return (
        encounter["risk_level"] in QUEUE_RISK_LEVELS
        and encounter["discharge_disposition_id"] not in EXCLUDED_DISCHARGE_DISPOSITIONS
    )


def create_encounter(encounter_data: Mapping[str, Any]) -> dict[str, Any]:
    """
    Score a new encounter, store it, and queue it for review when it is eligible.
    A new encounter has no readmission outcome yet, so readmitted is recorded as NO.
    """
    encounter = score_encounter({**encounter_data, "readmitted": "NO"})
    in_care_queue = is_queue_eligible(encounter)

    created = repository.insert_encounter(encounter, add_to_care_queue=in_care_queue)
    created["in_care_queue"] = in_care_queue
    return created


def search_encounters(
    patient_nbr: Optional[int] = None,
    risk_level: Optional[str] = None,
    risk_score: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    if risk_level is not None:
        risk_level = risk_level.strip().upper()
        if risk_level not in VALID_RISK_LEVELS:
            allowed_levels = ", ".join(sorted(VALID_RISK_LEVELS))
            raise ValueError(f"Invalid risk level. Allowed values: {allowed_levels}")

    return repository.search_encounters(
        patient_nbr=patient_nbr,
        risk_level=risk_level,
        risk_score=risk_score,
        limit=limit,
        offset=offset,
    )


def get_care_queue(
    high_only: bool = False,
    min_risk_score: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    risk_levels = ["HIGH"] if high_only else QUEUE_RISK_LEVELS
    return repository.get_care_queue(
        risk_levels=risk_levels,
        min_risk_score=min_risk_score,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Intervention workflow
# ---------------------------------------------------------------------------

def normalize_intervention_status(status: str) -> str:
    """
    Normalize and validate a workflow status value.
    """
    normalized_status = status.strip().upper()

    if normalized_status not in VALID_INTERVENTION_STATUSES:
        allowed_statuses = ", ".join(sorted(VALID_INTERVENTION_STATUSES))
        raise ValueError(f"Invalid intervention status. Allowed values: {allowed_statuses}")

    return normalized_status


def update_intervention(
    encounter_id: int,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """
    Update an intervention, distinguishing unknown encounters from encounters not in the queue.
    """
    encounter = get_encounter(encounter_id)

    if status is not None:
        status = normalize_intervention_status(status)

    intervention = repository.update_intervention(
        encounter_id=encounter_id,
        status=status,
        assigned_to=assigned_to,
        notes=notes,
    )

    if intervention is None:
        raise _not_in_queue_error(encounter)

    return intervention


def get_intervention(encounter_id: int) -> dict[str, Any]:
    """
    Fetch an encounter's intervention, distinguishing unknown encounters from encounters
    not in the queue.
    """
    encounter = get_encounter(encounter_id)
    intervention = repository.get_intervention_by_encounter_id(encounter_id)

    if intervention is None:
        raise _not_in_queue_error(encounter)

    return intervention


def _not_in_queue_error(encounter: Mapping[str, Any]) -> NotInCareQueueError:
    if encounter["risk_level"] not in QUEUE_RISK_LEVELS:
        reason = f"it is {encounter['risk_level']} risk (score {encounter['risk_score']})"
    else:
        reason = (
            f"discharge disposition {encounter['discharge_disposition_id']} "
            "(expired / hospice) is excluded from outreach"
        )
    return NotInCareQueueError(
        f"Encounter {encounter['encounter_id']} is not in the care queue because {reason}."
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def calculate_rate(numerator: int, denominator: int) -> float:
    """
    Calculate a percentage rate rounded to two decimal places.
    """
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def calculate_lift(group_rate: float, baseline_rate: float) -> float:
    """
    How many times higher a group's readmission rate is than the overall baseline.
    """
    if baseline_rate == 0:
        return 0.0
    return round(group_rate / baseline_rate, 2)


def get_operations_summary() -> dict[str, Any]:
    """
    Encounter risk tiers plus care-queue workload split into pending / in-progress / completed.
    """
    risk_counts = {
        row["risk_level"]: row["total_patients"]
        for row in repository.get_risk_level_outcomes()
    }
    status_counts = {
        row["status"]: row["count"]
        for row in repository.get_intervention_status_counts()
    }

    return {
        "total_encounters": sum(risk_counts.values()),
        "high_risk": risk_counts.get("HIGH", 0),
        "medium_risk": risk_counts.get("MEDIUM", 0),
        "low_risk": risk_counts.get("LOW", 0),
        "care_queue_size": sum(status_counts.values()),
        "excluded_from_queue": repository.count_excluded_from_queue(
            QUEUE_RISK_LEVELS, EXCLUDED_DISCHARGE_DISPOSITIONS
        ),
        "pending_interventions": status_counts.get("PENDING_REVIEW", 0),
        "in_progress_interventions": sum(
            status_counts.get(status, 0) for status in IN_PROGRESS_STATUSES
        ),
        "completed_interventions": status_counts.get("CLOSED", 0),
    }


def get_readmission_analysis() -> dict[str, Any]:
    """
    Evaluate the prioritization rule against historical <30-day readmissions.

    `readmitted` is only read here, after scoring, to measure the rule.
    """
    risk_rows = {row["risk_level"]: row for row in repository.get_risk_level_outcomes()}

    total = sum(row["total_patients"] for row in risk_rows.values())
    readmitted = sum(row["readmitted_under_30_days"] for row in risk_rows.values())
    baseline_rate = calculate_rate(readmitted, total)

    risk_groups = []
    for level in ["HIGH", "MEDIUM", "LOW"]:
        row = risk_rows.get(level, {"total_patients": 0, "readmitted_under_30_days": 0})
        rate = calculate_rate(row["readmitted_under_30_days"], row["total_patients"])
        risk_groups.append(
            {
                "risk_level": level,
                "total_patients": row["total_patients"],
                "readmitted_under_30_days": row["readmitted_under_30_days"],
                "readmission_rate": rate,
                "lift_vs_baseline": calculate_lift(rate, baseline_rate),
            }
        )

    membership = {row["in_queue"]: row for row in repository.get_queue_membership_outcomes()}
    queue_comparison = {}
    for key, in_queue in [("in_queue", True), ("not_in_queue", False)]:
        row = membership.get(in_queue, {"total_patients": 0, "readmitted_under_30_days": 0})
        rate = calculate_rate(row["readmitted_under_30_days"], row["total_patients"])
        queue_comparison[key] = {
            "total_patients": row["total_patients"],
            "readmitted_under_30_days": row["readmitted_under_30_days"],
            "readmission_rate": rate,
            "lift_vs_baseline": calculate_lift(rate, baseline_rate),
        }

    high = risk_groups[0]
    in_queue = queue_comparison["in_queue"]

    return {
        "high_risk_patients": high["total_patients"],
        "high_risk_readmitted_under_30_days": high["readmitted_under_30_days"],
        "high_risk_readmission_rate": high["readmission_rate"],
        "total_encounters": total,
        "readmitted_under_30_days": readmitted,
        "baseline_readmission_rate": baseline_rate,
        "queue_share_of_encounters": calculate_rate(in_queue["total_patients"], total),
        "queue_share_of_readmissions": calculate_rate(
            in_queue["readmitted_under_30_days"], readmitted
        ),
        "risk_groups": risk_groups,
        "queue_comparison": queue_comparison,
    }


def get_management_dashboard() -> dict[str, Any]:
    """
    Executive view: queue volume, workflow progress, and how well the queue targets readmissions.
    """
    summary = get_operations_summary()
    analysis = get_readmission_analysis()
    queue_by_level = {
        row["risk_level"]: row["count"]
        for row in repository.get_queue_counts_by_risk_level()
    }

    return {
        "total_encounters": summary["total_encounters"],
        "care_queue_size": summary["care_queue_size"],
        "high_risk_queue": queue_by_level.get("HIGH", 0),
        "medium_risk_queue": queue_by_level.get("MEDIUM", 0),
        "excluded_from_queue": summary["excluded_from_queue"],
        "pending_interventions": summary["pending_interventions"],
        "in_progress_interventions": summary["in_progress_interventions"],
        "completed_interventions": summary["completed_interventions"],
        "completion_rate": calculate_rate(
            summary["completed_interventions"], summary["care_queue_size"]
        ),
        "baseline_readmission_rate": analysis["baseline_readmission_rate"],
        "high_risk_readmission_rate": analysis["high_risk_readmission_rate"],
        "queue_readmission_rate": analysis["queue_comparison"]["in_queue"]["readmission_rate"],
        "queue_share_of_encounters": analysis["queue_share_of_encounters"],
        "queue_share_of_readmissions": analysis["queue_share_of_readmissions"],
    }
