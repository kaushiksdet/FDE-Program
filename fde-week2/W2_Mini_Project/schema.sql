-- Diabetes Readmission Intervention Queue schema
-- Run this after creating and connecting to the project database.

CREATE TABLE IF NOT EXISTS patient_encounters (
    encounter_id BIGINT PRIMARY KEY,
    patient_nbr BIGINT NOT NULL,
    age VARCHAR(20) NOT NULL,
    time_in_hospital INTEGER NOT NULL CHECK (time_in_hospital >= 0),
    number_inpatient INTEGER NOT NULL CHECK (number_inpatient >= 0),
    number_emergency INTEGER NOT NULL CHECK (number_emergency >= 0),
    number_outpatient INTEGER NOT NULL CHECK (number_outpatient >= 0),
    num_medications INTEGER NOT NULL CHECK (num_medications >= 0),
    num_lab_procedures INTEGER NOT NULL CHECK (num_lab_procedures >= 0),
    discharge_disposition_id INTEGER NOT NULL,
    admission_type_id INTEGER NOT NULL,
    readmitted VARCHAR(10) NOT NULL CHECK (readmitted IN ('NO', '>30', '<30')),
    risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 8),
    risk_level VARCHAR(10) NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH'))
);

CREATE TABLE IF NOT EXISTS care_interventions (
    intervention_id BIGSERIAL PRIMARY KEY,
    encounter_id BIGINT NOT NULL UNIQUE REFERENCES patient_encounters(encounter_id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_REVIEW'
        CHECK (status IN (
            'PENDING_REVIEW',
            'ASSIGNED',
            'CONTACTED',
            'FOLLOW_UP_SCHEDULED',
            'CLOSED'
        )),
    assigned_to VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS care_interventions_set_updated_at ON care_interventions;

CREATE TRIGGER care_interventions_set_updated_at
BEFORE UPDATE ON care_interventions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_patient_encounters_patient_nbr
    ON patient_encounters(patient_nbr);

CREATE INDEX IF NOT EXISTS idx_patient_encounters_risk_level_score
    ON patient_encounters(risk_level, risk_score DESC);

CREATE INDEX IF NOT EXISTS idx_patient_encounters_readmitted
    ON patient_encounters(readmitted);

CREATE INDEX IF NOT EXISTS idx_care_interventions_status
    ON care_interventions(status);

CREATE INDEX IF NOT EXISTS idx_care_interventions_assigned_to
    ON care_interventions(assigned_to);
