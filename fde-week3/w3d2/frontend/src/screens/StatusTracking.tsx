import { useEffect, useState, type FormEvent } from 'react'
import {
  INTERVENTION_STATUSES,
  getEncounter,
  getIntervention,
  updateIntervention,
  type Encounter,
  type Intervention,
  type InterventionStatus,
  type InterventionUpdate,
} from '../api'
import { Alert, EmptyState } from '../components/Alert'
import { RiskBadge, StatusBadge } from '../components/Badges'
import { Field } from '../components/Field'
import { ClipboardCheckIcon, HistoryIcon, SaveIcon, SearchIcon } from '../components/Icons'
import { statusLabel } from '../labels'
import { statusHref } from '../routes'

export interface UpdateLogEntry {
  id: number
  at: Date
  encounterId: number
  patientNbr: number
  changes: { field: string; from: string; to: string }[]
  status: InterventionStatus
}

interface Props {
  encounterId?: number
  updateLog: UpdateLogEntry[]
  onUpdated: (entry: UpdateLogEntry) => void
}

interface FormState {
  status: InterventionStatus
  assignedTo: string
  notes: string
}

const EMPTY_FORM: FormState = { status: 'PENDING_REVIEW', assignedTo: '', notes: '' }

function formFrom(record: Intervention): FormState {
  return { status: record.status, assignedTo: record.assigned_to ?? '', notes: record.notes ?? '' }
}

const FIELD_LABELS: Record<keyof InterventionUpdate, string> = {
  status: 'Status',
  assigned_to: 'Assigned To',
  notes: 'Notes',
}

export function StatusTracking({ encounterId, updateLog, onUpdated }: Props) {
  const [idInput, setIdInput] = useState(encounterId ? String(encounterId) : '')
  const [encounter, setEncounter] = useState<Encounter | null>(null)
  const [intervention, setIntervention] = useState<Intervention | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [loading, setLoading] = useState(Boolean(encounterId))
  const [reloadKey, setReloadKey] = useState(0)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const resetForLoad = () => {
    setLoading(true)
    setError(null)
    setSuccess(null)
    setEncounter(null)
    setIntervention(null)
  }

  // When the route's encounter changes (e.g. a link from the queue), reset during render
  // so the effect below only has to fetch.
  const [routeId, setRouteId] = useState(encounterId)
  if (encounterId !== routeId) {
    setRouteId(encounterId)
    if (encounterId) {
      setIdInput(String(encounterId))
      resetForLoad()
    }
  }

  useEffect(() => {
    if (!encounterId) return
    let cancelled = false
    getEncounter(encounterId)
      .then(async (found) => {
        if (cancelled) return
        setEncounter(found)
        const record = await getIntervention(encounterId)
        if (cancelled) return
        setIntervention(record)
        setForm(formFrom(record))
      })
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : String(err)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [encounterId, reloadKey])

  const handleLoad = (event: FormEvent) => {
    event.preventDefault()
    const id = idInput.trim()
    if (!/^\d+$/.test(id) || Number(id) <= 0) {
      setError('Encounter Id must be a positive whole number.')
      return
    }
    if (Number(id) === encounterId) {
      resetForLoad()
      setReloadKey((key) => key + 1)
    } else {
      window.location.hash = statusHref(Number(id))
    }
  }

  const pendingChanges = (): InterventionUpdate => {
    if (!intervention) return {}
    const changes: InterventionUpdate = {}
    if (form.status !== intervention.status) changes.status = form.status
    const assignedTo = form.assignedTo.trim()
    if (assignedTo !== (intervention.assigned_to ?? '')) changes.assigned_to = assignedTo
    const notes = form.notes.trim()
    if (notes !== (intervention.notes ?? '')) changes.notes = notes
    return changes
  }
  const changes = pendingChanges()
  const hasChanges = Object.keys(changes).length > 0

  const handleUpdate = async (event: FormEvent) => {
    event.preventDefault()
    if (!encounter || !intervention || !hasChanges) return

    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const before = intervention
      const updated = await updateIntervention(encounter.encounter_id, changes)
      setIntervention(updated)
      setForm(formFrom(updated))
      setSuccess(`Encounter ${updated.encounter_id} updated.`)
      onUpdated({
        id: Date.now(),
        at: new Date(updated.updated_at),
        encounterId: updated.encounter_id,
        patientNbr: encounter.patient_nbr,
        status: updated.status,
        changes: (Object.keys(changes) as (keyof InterventionUpdate)[]).map((field) => ({
          field: FIELD_LABELS[field],
          from: displayValue(field, before[field]),
          to: displayValue(field, updated[field]),
        })),
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  const editable = Boolean(intervention) && !loading

  return (
    <>
      <section className="card">
        <header className="card-header">
          <span className="card-icon">
            <ClipboardCheckIcon />
          </span>
          <div>
            <h2>Status Tracking</h2>
            <p>Load a queued encounter, then update its care status, owner and notes.</p>
          </div>
        </header>

        <form className="form" onSubmit={handleLoad} noValidate>
          <div className="form-grid">
            <Field label="Encounter Id">
              <div className="input-with-button">
                <input
                  inputMode="numeric"
                  value={idInput}
                  onChange={(event) => setIdInput(event.target.value)}
                  placeholder="e.g. 168920160"
                />
                <button type="submit" className="button secondary" disabled={loading}>
                  <SearchIcon size={16} />
                  {loading ? 'Loading…' : 'Load'}
                </button>
              </div>
            </Field>
            <Field label="Patient Number" hint="Filled from the encounter">
              <input value={encounter?.patient_nbr ?? ''} readOnly placeholder="—" />
            </Field>
          </div>
        </form>

        {encounter && (
          <div className="encounter-summary">
            <RiskBadge level={encounter.risk_level} score={encounter.risk_score} />
            <span>Age {encounter.age}</span>
            <span>{encounter.time_in_hospital} days in hospital</span>
            <span>{encounter.number_inpatient} inpatient</span>
            <span>{encounter.number_emergency} emergency</span>
            <span>{encounter.num_medications} medications</span>
            {intervention && <StatusBadge status={intervention.status} />}
          </div>
        )}

        <form className="form" onSubmit={handleUpdate} noValidate>
          <fieldset disabled={!editable} className="form-grid">
            <Field label="Status">
              <select
                value={form.status}
                onChange={(event) =>
                  setForm({ ...form, status: event.target.value as InterventionStatus })
                }
              >
                {INTERVENTION_STATUSES.map((value) => (
                  <option key={value} value={value}>
                    {statusLabel(value)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Assigned To">
              <input
                value={form.assignedTo}
                maxLength={100}
                onChange={(event) => setForm({ ...form, assignedTo: event.target.value })}
                placeholder="e.g. Care Team A"
              />
            </Field>
            <Field label="Notes">
              <textarea
                rows={3}
                value={form.notes}
                onChange={(event) => setForm({ ...form, notes: event.target.value })}
                placeholder="Outreach notes"
              />
            </Field>
          </fieldset>

          {error && <Alert kind="error">{error}</Alert>}
          {success && <Alert kind="success">{success}</Alert>}

          <div className="form-actions">
            {intervention && (
              <span className="muted small">
                Last updated {new Date(intervention.updated_at).toLocaleString()}
              </span>
            )}
            <button
              type="submit"
              className="button primary"
              disabled={!editable || !hasChanges || saving}
            >
              <SaveIcon size={16} />
              {saving ? 'Updating…' : 'Update'}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <header className="card-header compact">
          <span className="card-icon">
            <HistoryIcon />
          </span>
          <div>
            <h2>Updates</h2>
            <p>Changes made in this session, newest first.</p>
          </div>
        </header>
        {updateLog.length === 0 ? (
          <EmptyState>No updates yet.</EmptyState>
        ) : (
          <ul className="update-log">
            {updateLog.map((entry) => (
              <li key={entry.id}>
                <div className="update-log-head">
                  <a href={statusHref(entry.encounterId)}>Encounter {entry.encounterId}</a>
                  <span className="muted">Patient {entry.patientNbr}</span>
                  <StatusBadge status={entry.status} />
                  <span className="muted small push-right">{entry.at.toLocaleString()}</span>
                </div>
                <ul className="update-log-changes">
                  {entry.changes.map((change) => (
                    <li key={change.field}>
                      <strong>{change.field}:</strong> <span className="from">{change.from}</span>
                      {' → '}
                      <span className="to">{change.to}</span>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}

function displayValue(field: keyof InterventionUpdate, value: string | null): string {
  if (!value) return '(empty)'
  return field === 'status' ? statusLabel(value as InterventionStatus) : value
}
