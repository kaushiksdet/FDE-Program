// Typed client for the FastAPI service. Requests go to /api, which Vite proxies to uvicorn
// (see vite.config.ts), so the browser never needs CORS.

const API_BASE = '/api'

export const AGE_GROUPS = [
  '[0-10)',
  '[10-20)',
  '[20-30)',
  '[30-40)',
  '[40-50)',
  '[50-60)',
  '[60-70)',
  '[70-80)',
  '[80-90)',
  '[90-100)',
] as const

export const RISK_LEVELS = ['HIGH', 'MEDIUM', 'LOW'] as const

export const INTERVENTION_STATUSES = [
  'PENDING_REVIEW',
  'ASSIGNED',
  'CONTACTED',
  'FOLLOW_UP_SCHEDULED',
  'CLOSED',
] as const

export type AgeGroup = (typeof AGE_GROUPS)[number]
export type RiskLevel = (typeof RISK_LEVELS)[number]
export type InterventionStatus = (typeof INTERVENTION_STATUSES)[number]

export interface Encounter {
  encounter_id: number
  patient_nbr: number
  age: AgeGroup
  time_in_hospital: number
  number_inpatient: number
  number_emergency: number
  number_outpatient: number
  num_medications: number
  num_lab_procedures: number
  discharge_disposition_id: number
  admission_type_id: number
  readmitted: string
  risk_score: number
  risk_level: RiskLevel
}

export interface EncounterCreate {
  patient_nbr: number
  age: AgeGroup
  time_in_hospital: number
  number_inpatient: number
  number_emergency: number
  num_medications: number
}

export interface EncounterCreated extends Encounter {
  in_care_queue: boolean
}

export interface PatientSearchResult extends Encounter {
  intervention_id: number | null
  status: InterventionStatus | null
  assigned_to: string | null
  notes: string | null
  updated_at: string | null
}

export interface Intervention {
  intervention_id: number
  encounter_id: number
  status: InterventionStatus
  assigned_to: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface CareQueueItem extends Encounter {
  intervention_id: number
  status: InterventionStatus
  assigned_to: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface InterventionUpdate {
  status?: InterventionStatus
  assigned_to?: string
  notes?: string
}

export interface SearchFilters {
  patient_nbr?: number
  risk_level?: RiskLevel
  risk_score?: number
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** Turn FastAPI's `detail` (a string, or a list of 422 validation errors) into one message. */
function formatDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item: { loc?: unknown[]; msg?: string }) => {
        const field = item.loc?.filter((part) => part !== 'body' && part !== 'query').join('.')
        return field ? `${field}: ${item.msg}` : item.msg
      })
      .join('; ')
  }
  return 'Unexpected error'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the API. Is uvicorn running?')
  }

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    try {
      message = formatDetail((await response.json()).detail)
    } catch {
      // Non-JSON error body (e.g. proxy error); keep the status text.
    }
    throw new ApiError(response.status, message)
  }

  return response.json() as Promise<T>
}

function toQuery(params: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') query.set(key, String(value))
  }
  const text = query.toString()
  return text ? `?${text}` : ''
}

export function createEncounter(payload: EncounterCreate): Promise<EncounterCreated> {
  return request('/encounters', { method: 'POST', body: JSON.stringify(payload) })
}

export function getEncounter(encounterId: number): Promise<Encounter> {
  return request(`/encounters/${encounterId}`)
}

export function searchEncounters(
  filters: SearchFilters,
  limit = 100,
  offset = 0,
): Promise<PatientSearchResult[]> {
  return request(`/encounters/search${toQuery({ ...filters, limit, offset })}`)
}

export function getHighRiskQueue(limit = 25, offset = 0): Promise<CareQueueItem[]> {
  return request(`/care-queue/high${toQuery({ limit, offset })}`)
}

export function getIntervention(encounterId: number): Promise<Intervention> {
  return request(`/interventions/${encounterId}`)
}

export function updateIntervention(
  encounterId: number,
  payload: InterventionUpdate,
): Promise<Intervention> {
  return request(`/interventions/${encounterId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
