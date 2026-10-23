import { useState, type FormEvent } from 'react'
import { AGE_GROUPS, createEncounter, type AgeGroup, type EncounterCreated } from '../api'
import { Alert } from '../components/Alert'
import { Field } from '../components/Field'
import { RiskBadge } from '../components/Badges'
import { ChevronRightIcon, UserPlusIcon } from '../components/Icons'
import { statusHref } from '../routes'

type NumberField =
  | 'patient_nbr'
  | 'time_in_hospital'
  | 'number_inpatient'
  | 'number_emergency'
  | 'num_medications'

const NUMBER_FIELDS: { name: NumberField; label: string; min: number }[] = [
  { name: 'time_in_hospital', label: 'Time in Hospital (days)', min: 0 },
  { name: 'number_inpatient', label: 'Inpatient Visits', min: 0 },
  { name: 'number_emergency', label: 'Emergency Visits', min: 0 },
  { name: 'num_medications', label: 'Medications', min: 0 },
]

type FormState = Record<NumberField, string> & { age: AgeGroup | '' }

const EMPTY_FORM: FormState = {
  patient_nbr: '',
  age: '',
  time_in_hospital: '',
  number_inpatient: '',
  number_emergency: '',
  num_medications: '',
}

function validate(form: FormState): Partial<Record<keyof FormState, string>> {
  const errors: Partial<Record<keyof FormState, string>> = {}

  const patient = form.patient_nbr.trim()
  if (!patient) errors.patient_nbr = 'Required'
  else if (!/^\d+$/.test(patient) || Number(patient) <= 0) errors.patient_nbr = 'Enter a positive whole number'

  if (!form.age) errors.age = 'Select an age group'

  for (const { name } of NUMBER_FIELDS) {
    const value = form[name].trim()
    if (!value) errors[name] = 'Required'
    else if (!/^\d+$/.test(value)) errors[name] = 'Enter a whole number, 0 or more'
  }

  return errors
}

export function AddEncounter() {
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)
  const [created, setCreated] = useState<EncounterCreated | null>(null)

  const setField = (name: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setServerError(null)
    setCreated(null)

    const validationErrors = validate(form)
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) return

    setSubmitting(true)
    try {
      const result = await createEncounter({
        patient_nbr: Number(form.patient_nbr),
        age: form.age as AgeGroup,
        time_in_hospital: Number(form.time_in_hospital),
        number_inpatient: Number(form.number_inpatient),
        number_emergency: Number(form.number_emergency),
        num_medications: Number(form.num_medications),
      })
      setCreated(result)
      setForm(EMPTY_FORM)
    } catch (error) {
      setServerError(error instanceof Error ? error.message : String(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="card">
      <header className="card-header">
        <span className="card-icon">
          <UserPlusIcon />
        </span>
        <div>
          <h2>Add Patient Encounter</h2>
          <p>Risk score and care-queue placement are calculated automatically.</p>
        </div>
      </header>

      <form className="form" onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          <Field label="Patient Number" error={errors.patient_nbr}>
            <input
              inputMode="numeric"
              value={form.patient_nbr}
              onChange={(event) => setField('patient_nbr', event.target.value)}
              placeholder="e.g. 8222157"
            />
          </Field>

          <Field label="Age" error={errors.age}>
            <select value={form.age} onChange={(event) => setField('age', event.target.value)}>
              <option value="">Age Group</option>
              {AGE_GROUPS.map((group) => (
                <option key={group} value={group}>
                  {group.replace('[', '').replace(')', '')} years
                </option>
              ))}
            </select>
          </Field>

          {NUMBER_FIELDS.map(({ name, label, min }) => (
            <Field key={name} label={label} error={errors[name]}>
              <input
                type="number"
                min={min}
                step={1}
                value={form[name]}
                onChange={(event) => setField(name, event.target.value)}
              />
            </Field>
          ))}
        </div>

        {serverError && <Alert kind="error">{serverError}</Alert>}

        {created && (
          <Alert kind="success">
            <strong>Encounter {created.encounter_id} added</strong> for patient {created.patient_nbr}.{' '}
            Risk <RiskBadge level={created.risk_level} score={created.risk_score} />{' '}
            {created.in_care_queue ? (
              <>
                — added to the care queue.{' '}
                <a href={statusHref(created.encounter_id)}>Track status</a>
              </>
            ) : (
              '— not queued (LOW risk).'
            )}
          </Alert>
        )}

        <div className="form-actions">
          <button type="submit" className="button primary" disabled={submitting}>
            {submitting ? 'Adding…' : 'Add'}
            <ChevronRightIcon />
          </button>
        </div>
      </form>
    </section>
  )
}
