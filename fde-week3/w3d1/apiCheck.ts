import type {Encounter} from "./Encounter.ts";
import type {Intervention} from "./Intervnetions.ts";


async function apiCallEnconunterID(encounter_id : number): Promise<void> {
    const response = await fetch(`http://127.0.0.1:3003/encounters/${encounter_id}`);
    console.log(response.status);
    let data: Encounter = await response.json();
    console.log(data);
}

apiCallEnconunterID(2278392);

async function apiCallEnconunters(): Promise<void> {
    const response = await fetch(`http://127.0.0.1:3003/encounters`);
    console.log(response.status);
    let data: Encounter[] = await response.json();
    console.log(data);
    console.log(data.length);
}

//apiCallEnconunters();

async function  apiCallInterventions(): Promise<void> {
    const response = await fetch(`http://127.0.0.1:3003/care-queue`);
    console.log(response.status);
    let data: Intervention[] = await response.json();
    console.log(data);
}

//apiCallInterventions();

async function apiCallCreateEncounter() {
       const patient ={
    "encounter_id": 3,
    "patient_nbr": 112345,
    "age": "20-30",
    "time_in_hospital": 10,
    "number_inpatient": 10,
    "number_emergency": 5,
    "number_outpatient": 0,
    "num_medications": 5,
    "num_lab_procedures": 0,
    "discharge_disposition_id": 0,
    "admission_type_id": 0,
    "readmitted": "0",
    "risk_score": 6.0,
    "risk_level": "HIGH"
    }
        try {
            const response = await fetch('http://127.0.0.1:3003/createencounters', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(patient)
            });
            const result = await response.json();
            console.log(result);
             // Refresh the table after submission
            } catch (error) {
            console.error('There was a problem with the fetch operation:', error);
            }
}

//apiCallCreateEncounter();

async function apiCallUpdateIntervention(intervention_id: number, assigned_to: string): Promise<void> {
    const payload = {
        assigned_to: assigned_to
    };
    const response = await fetch(`http://127.0.0.1:3003/update-interventions/${intervention_id}?assigned_to=${encodeURIComponent(assigned_to)}`, {
        method: 'PATCH'
        });
        
    const result = await response.json();
    console.log(result);
}

//apiCallUpdateIntervention(6, "care team A");

async function apiCallInterventionById(intervention_id: number): Promise<void> {
    const response = await fetch(`http://127.0.0.1:3003/interventions/${intervention_id}`);
    console.log(response.status);
    let data: Intervention = await response.json();
    console.log(data);
}

apiCallInterventionById(6);


async function apiCallOperationSummary(): Promise<void> {
    const response = await fetch(`http://127.0.0.1:3003/operational-summary`);
    console.log(response.status);
    let data: any = await response.json();
    console.log(data);
}

apiCallOperationSummary();

async function apiCallReadmissions(): Promise<void> {
    const response = await fetch(`http://127.0.0.1:3003/readmission-risk-analysis`);
    console.log(response.status);
    let data: any = await response.json();
    console.log(data);
}

apiCallReadmissions();

async function apiCallExecutiveSummary(): Promise<void> {
    const response = await fetch(`http://127.0.0.1:3003/executive-summary`);
    console.log(response.status);
    let data: any = await response.json();
    console.log(data);
}

apiCallExecutiveSummary();

async function apiCallSearchPatient(
    { patient_number, risk_score, risk_level }:
    { patient_number?: string; risk_score?: number; risk_level?: string } = {}
): Promise<void> {
    const url = new URL(`http://127.0.0.1:3003/searchPatient`);
    if (patient_number) url.searchParams.append('patient_number', patient_number);
    if (risk_score !== undefined) url.searchParams.append('risk_score', risk_score.toString());
    if (risk_level) url.searchParams.append('risk_level', risk_level);

    const response = await fetch(url);
    console.log(response.status);
    let data: any = await response.json();
    console.log(data);
}

// Example usage:
apiCallSearchPatient({ risk_level: "HIGH" });