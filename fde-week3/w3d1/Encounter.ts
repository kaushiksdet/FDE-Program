export {Encounter};

interface Encounter {
    encounter_id: number;
    patient_nbr: number;
    age: string;
    time_in_hospital: number;
    number_inpatient: number;
    number_emergency: number;
    number_outpatient: number;
    num_medications: number;
    num_lab_procedures: number;
    discharge_disposition_id: number;
    admission_type_id: number;
    readmitted: string;
    risk_score: number;
    risk_level: string;
}