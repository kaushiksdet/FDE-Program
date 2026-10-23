from pathlib import Path

import pandas as pd

import repository
from service import (
    REQUIRED_DATASET_COLUMNS,
    VALID_READMITTED_VALUES,
    score_encounter,
    sync_care_queue,
)


DATA_FILE = Path(__file__).resolve().parent / "data" / "diabetic_data.csv"

INTEGER_COLUMNS = [
    "encounter_id",
    "patient_nbr",
    "time_in_hospital",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "num_medications",
    "num_lab_procedures",
    "discharge_disposition_id",
    "admission_type_id",
]

# Counts that cannot be negative.
NON_NEGATIVE_COLUMNS = [
    "time_in_hospital",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "num_medications",
    "num_lab_procedures",
]


def load_dataset(csv_path: Path = DATA_FILE) -> pd.DataFrame:
    """
    Load only the required columns from the diabetes CSV. The dataset marks missing values as '?'.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    return pd.read_csv(
        csv_path,
        usecols=REQUIRED_DATASET_COLUMNS,
        na_values=["?", ""],
        dtype=str,
    )


def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Drop rows that cannot be scored or evaluated reliably, and report how many were dropped and why.
    Rows are dropped rather than imputed: guessing utilization counts would distort the risk score.
    """
    report = {"rows_read": len(df)}

    df = df.apply(lambda column: column.str.strip())

    before = len(df)
    df = df.dropna(subset=REQUIRED_DATASET_COLUMNS)
    report["dropped_missing_values"] = before - len(df)

    for column in INTEGER_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    before = len(df)
    df = df.dropna(subset=INTEGER_COLUMNS)
    report["dropped_non_numeric"] = before - len(df)
    df[INTEGER_COLUMNS] = df[INTEGER_COLUMNS].astype(int)

    before = len(df)
    df = df[(df[NON_NEGATIVE_COLUMNS] >= 0).all(axis=1)]
    report["dropped_negative_counts"] = before - len(df)

    df["readmitted"] = df["readmitted"].str.upper()
    before = len(df)
    df = df[df["readmitted"].isin(VALID_READMITTED_VALUES)]
    report["dropped_invalid_readmitted"] = before - len(df)

    before = len(df)
    df = df.drop_duplicates(subset="encounter_id", keep="first")
    report["dropped_duplicate_encounters"] = before - len(df)

    report["rows_kept"] = len(df)
    return df, report


def prepare_encounters(df: pd.DataFrame) -> list[dict]:
    """
    Convert DataFrame rows into dictionaries and assign calculated risk scores to each encounter.
    """
    records = df.to_dict(orient="records")
    return [score_encounter(record) for record in records]


def main():
    """
    Orchestrate the loading pipeline: read CSV, clean, score, persist encounters, and sync the
    care queue. Safe to re-run: encounters are upserted and existing intervention work is kept.
    """
    print(f"Loading dataset from {DATA_FILE}")

    raw_df = load_dataset(DATA_FILE)
    df, report = clean_dataset(raw_df)

    print("Data cleanup report:")
    for key, value in report.items():
        print(f"  {key:<30} {value}")

    scored_records = prepare_encounters(df)
    encounter_count = repository.upsert_patient_encounters(scored_records)
    queue_changes = sync_care_queue()

    print(f"Loaded {encounter_count} patient encounters.")
    print(f"Created {queue_changes['created']} new care intervention records.")
    print(f"Removed {queue_changes['removed']} ineligible, untouched care intervention records.")
    print("Data loading complete.")


if __name__ == "__main__":
    main()
