"""
Data-access layer. Every function here only runs parameterized SQL and returns rows;
business rules (risk thresholds, queue eligibility, rates) live in service.py.
"""

from typing import Any, Optional

from psycopg2.extras import execute_values

from database import get_connection, get_dict_connection


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

INTERVENTION_SELECT_COLUMNS = """
    intervention_id,
    encounter_id,
    status,
    assigned_to,
    notes,
    created_at,
    updated_at
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


def _execute_write(sql: str, params: tuple[Any, ...] = ()) -> int:
    """
    Execute an INSERT/UPDATE/DELETE statement in its own transaction and return the row count.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            affected = cursor.rowcount
        conn.commit()
        return affected
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Encounters
# ---------------------------------------------------------------------------

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


def search_encounters(
    patient_nbr: Optional[int] = None,
    risk_level: Optional[str] = None,
    risk_score: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Search encounters by any combination of patient number, risk level and exact risk score,
    including the care intervention status when the encounter is in the queue.
    """
    where_clauses = []
    params: list[Any] = []

    if patient_nbr is not None:
        where_clauses.append("e.patient_nbr = %s")
        params.append(patient_nbr)

    if risk_level is not None:
        where_clauses.append("e.risk_level = %s")
        params.append(risk_level)

    if risk_score is not None:
        where_clauses.append("e.risk_score = %s")
        params.append(risk_score)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    params.extend([limit, offset])

    sql = f"""
        SELECT
            {", ".join(f"e.{column}" for column in PATIENT_ENCOUNTER_COLUMNS)},
            i.intervention_id,
            i.status,
            i.assigned_to,
            i.notes,
            i.updated_at
        FROM patient_encounters e
        LEFT JOIN care_interventions i ON i.encounter_id = e.encounter_id
        {where_sql}
        ORDER BY e.risk_score DESC, e.encounter_id
        LIMIT %s OFFSET %s;
    """
    return _fetch_all(sql, tuple(params))


def insert_encounter(encounter: dict[str, Any], add_to_care_queue: bool) -> dict[str, Any]:
    """
    Insert one new encounter with the next encounter_id and, when add_to_care_queue is set,
    its PENDING_REVIEW intervention, in a single transaction. The table lock serializes
    concurrent inserts so two requests cannot claim the same encounter_id.
    """
    columns = [column for column in PATIENT_ENCOUNTER_COLUMNS if column != "encounter_id"]

    sql = f"""
        INSERT INTO patient_encounters (encounter_id, {", ".join(columns)})
        SELECT COALESCE(MAX(encounter_id), 0) + 1, {", ".join(["%s"] * len(columns))}
        FROM patient_encounters
        RETURNING {ENCOUNTER_SELECT_COLUMNS};
    """

    conn = get_dict_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("LOCK TABLE patient_encounters IN SHARE ROW EXCLUSIVE MODE;")
            cursor.execute(sql, tuple(encounter[column] for column in columns))
            row = dict(cursor.fetchone())
            if add_to_care_queue:
                cursor.execute(
                    "INSERT INTO care_interventions (encounter_id) VALUES (%s);",
                    (row["encounter_id"],),
                )
        conn.commit()
        return row
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Care queue and interventions
# ---------------------------------------------------------------------------

def get_care_queue(
    risk_levels: list[str],
    min_risk_score: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Retrieve care queue records for the given risk levels, highest priority first.
    """
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
            e.risk_score DESC,
            e.number_inpatient DESC,
            e.number_emergency DESC,
            e.encounter_id
        LIMIT %s OFFSET %s;
    """
    return _fetch_all(sql, tuple(params))


def get_intervention_by_encounter_id(encounter_id: int) -> Optional[dict[str, Any]]:
    """
    Fetch care intervention details for a specific encounter ID.
    """
    sql = f"""
        SELECT {INTERVENTION_SELECT_COLUMNS}
        FROM care_interventions
        WHERE encounter_id = %s;
    """
    return _fetch_one(sql, (encounter_id,))


def update_intervention(
    encounter_id: int,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Update intervention workflow attributes (status, assignee, notes) for a given encounter ID.
    Column names are fixed in code; only values are passed as parameters.
    """
    updates = []
    params: list[Any] = []

    if status is not None:
        updates.append("status = %s")
        params.append(status)

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
        RETURNING {INTERVENTION_SELECT_COLUMNS};
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


def create_care_interventions(
    risk_levels: list[str],
    excluded_dispositions: list[int],
) -> int:
    """
    Create a PENDING_REVIEW intervention for each eligible encounter that does not have one yet.
    """
    sql = """
        INSERT INTO care_interventions (encounter_id)
        SELECT encounter_id
        FROM patient_encounters
        WHERE risk_level = ANY(%s)
          AND NOT (discharge_disposition_id = ANY(%s))
        ON CONFLICT (encounter_id) DO NOTHING;
    """
    return _execute_write(sql, (risk_levels, excluded_dispositions))


def delete_ineligible_untouched_interventions(
    risk_levels: list[str],
    excluded_dispositions: list[int],
) -> int:
    """
    Remove queue entries that are no longer eligible, but only if nobody has worked them yet
    (still PENDING_REVIEW with no owner or notes), so care-team work is never discarded.
    """
    sql = """
        DELETE FROM care_interventions i
        USING patient_encounters e
        WHERE i.encounter_id = e.encounter_id
          AND i.status = 'PENDING_REVIEW'
          AND i.assigned_to IS NULL
          AND i.notes IS NULL
          AND (
              NOT (e.risk_level = ANY(%s))
              OR e.discharge_disposition_id = ANY(%s)
          );
    """
    return _execute_write(sql, (risk_levels, excluded_dispositions))


# ---------------------------------------------------------------------------
# Aggregates for metrics (rates and derived values are computed in service.py)
# ---------------------------------------------------------------------------

def get_risk_level_outcomes() -> list[dict[str, Any]]:
    """
    Count encounters and historical <30-day readmissions per risk level.
    """
    sql = """
        SELECT
            risk_level,
            COUNT(*) AS total_patients,
            COUNT(*) FILTER (WHERE readmitted = '<30') AS readmitted_under_30_days
        FROM patient_encounters
        GROUP BY risk_level;
    """
    return _fetch_all(sql)


def get_queue_membership_outcomes() -> list[dict[str, Any]]:
    """
    Count encounters and historical <30-day readmissions for in-queue vs not-in-queue encounters.
    """
    sql = """
        SELECT
            (i.encounter_id IS NOT NULL) AS in_queue,
            COUNT(*) AS total_patients,
            COUNT(*) FILTER (WHERE e.readmitted = '<30') AS readmitted_under_30_days
        FROM patient_encounters e
        LEFT JOIN care_interventions i ON i.encounter_id = e.encounter_id
        GROUP BY (i.encounter_id IS NOT NULL);
    """
    return _fetch_all(sql)


def get_intervention_status_counts() -> list[dict[str, Any]]:
    """
    Count care interventions per workflow status.
    """
    sql = """
        SELECT status, COUNT(*) AS count
        FROM care_interventions
        GROUP BY status;
    """
    return _fetch_all(sql)


def get_queue_counts_by_risk_level() -> list[dict[str, Any]]:
    """
    Count care queue entries per risk level.
    """
    sql = """
        SELECT e.risk_level, COUNT(*) AS count
        FROM care_interventions i
        JOIN patient_encounters e ON e.encounter_id = i.encounter_id
        GROUP BY e.risk_level;
    """
    return _fetch_all(sql)


def count_excluded_from_queue(
    risk_levels: list[str],
    excluded_dispositions: list[int],
) -> int:
    """
    Count encounters that meet the risk threshold but are excluded by discharge disposition.
    """
    sql = """
        SELECT COUNT(*) AS count
        FROM patient_encounters
        WHERE risk_level = ANY(%s)
          AND discharge_disposition_id = ANY(%s);
    """
    row = _fetch_one(sql, (risk_levels, excluded_dispositions))
    return row["count"] if row else 0
