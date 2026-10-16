from typing import Any, Optional

from psycopg2.extras import execute_values

from database import get_connection, get_dict_connection
from service import calculate_rate, normalize_intervention_status


PATIENT_ENCOUNTER_COLUMNS = [
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
    "risk_score",
    "risk_level",
]

ENCOUNTER_SELECT_COLUMNS = """
    encounter_id,
    patient_nbr,
    age,
    time_in_hospital,
    number_inpatient,
    number_emergency,
    number_outpatient,
    num_medications,
    num_lab_procedures,
    discharge_disposition_id,
    admission_type_id,
    readmitted,
    risk_score,
    risk_level
"""

CARE_QUEUE_SELECT_COLUMNS = """
    e.encounter_id,
    e.patient_nbr,
    e.age,
    e.time_in_hospital,
    e.number_inpatient,
    e.number_emergency,
    e.number_outpatient,
    e.num_medications,
    e.num_lab_procedures,
    e.discharge_disposition_id,
    e.admission_type_id,
    e.readmitted,
    e.risk_score,
    e.risk_level,
    i.intervention_id,
    i.status,
    i.assigned_to,
    i.notes,
    i.created_at,
    i.updated_at
"""


def _fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """
    Execute a SELECT query and return all matching rows as a list of dictionaries.
    """
    conn = get_dict_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def _fetch_one(sql: str, params: tuple[Any, ...] = ()) -> Optional[dict[str, Any]]:
    """
    Execute a SELECT query and return a single row as a dictionary, or None if not found.
    """
    conn = get_dict_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_encounters(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """
    Retrieve a paginated list of patient encounters ordered by encounter_id.
    """
    sql = f"""
        SELECT {ENCOUNTER_SELECT_COLUMNS}
        FROM patient_encounters
        ORDER BY encounter_id
        LIMIT %s OFFSET %s;
    """
    return _fetch_all(sql, (limit, offset))


def get_encounter_by_id(encounter_id: int) -> Optional[dict[str, Any]]:
    """
    Fetch a single patient encounter by its encounter ID.
    """
    sql = f"""
        SELECT {ENCOUNTER_SELECT_COLUMNS}
        FROM patient_encounters
        WHERE encounter_id = %s;
    """
    return _fetch_one(sql, (encounter_id,))


def get_care_queue(
    high_only: bool = False,
    min_risk_score: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Retrieve prioritized care queue records for medium and high risk encounters with optional filters.
    """
    risk_levels = ["HIGH"] if high_only else ["MEDIUM", "HIGH"]
    where_clauses = ["e.risk_level = ANY(%s)"]
    params: list[Any] = [risk_levels]

    if min_risk_score is not None:
        where_clauses.append("e.risk_score >= %s")
        params.append(min_risk_score)

    params.extend([limit, offset])

    sql = f"""
        SELECT {CARE_QUEUE_SELECT_COLUMNS}
        FROM patient_encounters e
        JOIN care_interventions i ON i.encounter_id = e.encounter_id
        WHERE {" AND ".join(where_clauses)}
        ORDER BY
            CASE e.risk_level WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
            e.risk_score DESC,
            e.number_inpatient DESC,
            e.number_emergency DESC,
            e.encounter_id
        LIMIT %s OFFSET %s;
    """
    return _fetch_all(sql, tuple(params))


def update_intervention(
    encounter_id: int,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Update intervention workflow attributes (status, assignee, notes) for a given encounter ID.
    """
    updates = []
    params: list[Any] = []

    if status is not None:
        updates.append("status = %s")
        params.append(normalize_intervention_status(status))

    if assigned_to is not None:
        updates.append("assigned_to = %s")
        params.append(assigned_to)

    if notes is not None:
        updates.append("notes = %s")
        params.append(notes)

    if not updates:
        return get_intervention_by_encounter_id(encounter_id)

    params.append(encounter_id)

    sql = f"""
        UPDATE care_interventions
        SET {", ".join(updates)}
        WHERE encounter_id = %s
        RETURNING
            intervention_id,
            encounter_id,
            status,
            assigned_to,
            notes,
            created_at,
            updated_at;
    """
    conn = get_dict_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
        conn.commit()
        return dict(row) if row else None
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_intervention_by_encounter_id(encounter_id: int) -> Optional[dict[str, Any]]:
    """
    Fetch care intervention details for a specific encounter ID.
    """
    sql = """
        SELECT
            intervention_id,
            encounter_id,
            status,
            assigned_to,
            notes,
            created_at,
            updated_at
        FROM care_interventions
        WHERE encounter_id = %s;
    """
    return _fetch_one(sql, (encounter_id,))


def get_operations_summary() -> dict[str, Any]:
    """
    Calculate high-level operational counts across encounter risk tiers and intervention statuses.
    """
    sql = """
        SELECT
            COUNT(*) AS total_encounters,
            COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk,
            COUNT(*) FILTER (WHERE risk_level = 'MEDIUM') AS medium_risk,
            COUNT(*) FILTER (WHERE risk_level = 'LOW') AS low_risk,
            (
                SELECT COUNT(*)
                FROM care_interventions
                WHERE status <> 'CLOSED'
            ) AS pending_interventions,
            (
                SELECT COUNT(*)
                FROM care_interventions
                WHERE status = 'CLOSED'
            ) AS completed_interventions
        FROM patient_encounters;
    """
    return _fetch_one(sql) or {}


def get_readmission_analysis() -> dict[str, Any]:
    """
    Calculate 30-day readmission totals and rates overall and grouped by patient risk level.
    """
    total_sql = """
        SELECT
            COUNT(*) AS total_encounters,
            COUNT(*) FILTER (WHERE readmitted = '<30') AS readmitted_under_30_days
        FROM patient_encounters;
    """
    groups_sql = """
        SELECT
            risk_level,
            COUNT(*) AS total_patients,
            COUNT(*) FILTER (WHERE readmitted = '<30') AS readmitted_under_30_days
        FROM patient_encounters
        GROUP BY risk_level
        ORDER BY CASE risk_level WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END;
    """

    total_row = _fetch_one(total_sql) or {
        "total_encounters": 0,
        "readmitted_under_30_days": 0,
    }
    group_rows = _fetch_all(groups_sql)

    total_row["readmission_rate"] = calculate_rate(
        total_row["readmitted_under_30_days"],
        total_row["total_encounters"],
    )

    for row in group_rows:
        row["readmission_rate"] = calculate_rate(
            row["readmitted_under_30_days"],
            row["total_patients"],
        )

    total_row["risk_groups"] = group_rows
    return total_row


def get_management_dashboard() -> dict[str, Any]:
    """
    Aggregate key summary metrics and high-risk readmission rate for executive leadership.
    """
    summary = get_operations_summary()
    analysis = get_readmission_analysis()

    high_risk_readmission_rate = 0.0
    for group in analysis["risk_groups"]:
        if group["risk_level"] == "HIGH":
            high_risk_readmission_rate = group["readmission_rate"]
            break

    return {
        "total_encounters": summary.get("total_encounters", 0),
        "care_queue_size": summary.get("high_risk", 0) + summary.get("medium_risk", 0),
        "high_risk_queue": summary.get("high_risk", 0),
        "medium_risk_queue": summary.get("medium_risk", 0),
        "pending_interventions": summary.get("pending_interventions", 0),
        "completed_interventions": summary.get("completed_interventions", 0),
        "high_risk_readmission_rate": high_risk_readmission_rate,
    }


def upsert_patient_encounters(records: list[dict[str, Any]]) -> int:
    """
    Insert or update multiple patient encounter records in batch mode.
    """
    if not records:
        return 0

    values = [
        tuple(record[column] for column in PATIENT_ENCOUNTER_COLUMNS)
        for record in records
    ]

    sql = """
        INSERT INTO patient_encounters (
            encounter_id,
            patient_nbr,
            age,
            time_in_hospital,
            number_inpatient,
            number_emergency,
            number_outpatient,
            num_medications,
            num_lab_procedures,
            discharge_disposition_id,
            admission_type_id,
            readmitted,
            risk_score,
            risk_level
        )
        VALUES %s
        ON CONFLICT (encounter_id) DO UPDATE SET
            patient_nbr = EXCLUDED.patient_nbr,
            age = EXCLUDED.age,
            time_in_hospital = EXCLUDED.time_in_hospital,
            number_inpatient = EXCLUDED.number_inpatient,
            number_emergency = EXCLUDED.number_emergency,
            number_outpatient = EXCLUDED.number_outpatient,
            num_medications = EXCLUDED.num_medications,
            num_lab_procedures = EXCLUDED.num_lab_procedures,
            discharge_disposition_id = EXCLUDED.discharge_disposition_id,
            admission_type_id = EXCLUDED.admission_type_id,
            readmitted = EXCLUDED.readmitted,
            risk_score = EXCLUDED.risk_score,
            risk_level = EXCLUDED.risk_level;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            execute_values(cursor, sql, values, page_size=1000)
        conn.commit()
        return len(records)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_care_interventions_for_queue() -> int:
    """
    Populate care_interventions table for encounters classified as MEDIUM or HIGH risk.
    """
    sql = """
        INSERT INTO care_interventions (encounter_id)
        SELECT encounter_id
        FROM patient_encounters
        WHERE risk_level IN ('MEDIUM', 'HIGH')
        ON CONFLICT (encounter_id) DO NOTHING;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            inserted_count = cursor.rowcount
        conn.commit()
        return inserted_count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
