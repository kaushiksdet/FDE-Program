from pathlib import Path

import pandas as pd

from repository import create_care_interventions_for_queue, upsert_patient_encounters
from service import REQUIRED_DATASET_COLUMNS, score_encounter


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


def load_dataset(csv_path: Path = DATA_FILE) -> pd.DataFrame:
    """
    Load the diabetes CSV dataset, filter for required columns, and cast column types.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = pd.read_csv(csv_path, usecols=REQUIRED_DATASET_COLUMNS)

    for column in INTEGER_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="raise").astype(int)

    df["age"] = df["age"].astype(str)
    df["readmitted"] = df["readmitted"].astype(str)

    return df


def prepare_encounters(df: pd.DataFrame) -> list[dict]:
    """
    Convert DataFrame rows into dictionaries and assign calculated risk scores to each encounter.
    """
    records = df.to_dict(orient="records")
    return [score_encounter(record) for record in records]


def main():
    """
    Orchestrate the loading pipeline: read CSV, calculate risk scores, and persist encounters and care queue interventions in the database.
    """
    print(f"Loading dataset from {DATA_FILE}")

    df = load_dataset(DATA_FILE)
    scored_records = prepare_encounters(df)

    encounter_count = upsert_patient_encounters(scored_records)
    intervention_count = create_care_interventions_for_queue()

    print(f"Loaded {encounter_count} patient encounters.")
    print(f"Created {intervention_count} new care intervention records.")
    print("Data loading complete.")


if __name__ == "__main__":
    main()
