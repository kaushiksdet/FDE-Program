import { Encounter }from "./Encounter";

const encounter: Encounter = {
    encounter_id: 12345,
    patient_nbr: 67890,
    age: "45-50",
    time_in_hospital: 5,
    number_inpatient: 2,
    number_emergency: 1,
    number_outpatient: 3,
    num_medications: 10,
    num_lab_procedures: 15,
    discharge_disposition_id: 1,
    admission_type_id: 2,
    readmitted: "NO",
    risk_score: 0.75,
    risk_level: "Medium"
};

const encounter1: Encounter = {
    encounter_id: 54321,
    patient_nbr: 98765,
    age: "30-35",
    time_in_hospital: 3,
    number_inpatient: 1,
    number_emergency: 0,
    number_outpatient: 2,
    num_medications: 5,
    num_lab_procedures: 8,
    discharge_disposition_id: 2,
    admission_type_id: 1,
    readmitted: "YES",
    risk_score: 0.85,
    risk_level: "High"
};

const encounters: Encounter[] = [encounter, encounter1];

console.log(encounters);