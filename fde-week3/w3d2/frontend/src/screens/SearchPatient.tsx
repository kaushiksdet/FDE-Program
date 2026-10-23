import { useState, type FormEvent } from 'react'
import {
  RISK_LEVELS,
  searchEncounters,
  type PatientSearchResult,
  type RiskLevel,
  type SearchFilters,
} from '../api'
import { Alert, EmptyState } from '../components/Alert'
import { RiskBadge, StatusBadge } from '../components/Badges'
import { Field } from '../components/Field'
import { ChevronRightIcon, InboxIcon, SearchIcon } from '../components/Icons'
import { statusHref } from '../routes'

const RESULT_LIMIT = 100

export function SearchPatient() {
  const [patientNbr, setPatientNbr] = useState('')
  const [riskLevel, setRiskLevel] = useState<RiskLevel | ''>('')
  const [riskScore, setRiskScore] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<PatientSearchResult[] | null>(null)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    const filters: SearchFilters = {}
    const patient = patientNbr.trim()
    const score = riskScore.trim()

    if (patient) {
      if (!/^\d+$/.test(patient) || Number(patient) <= 0) {
        return setFormError('Patient Number must be a positive whole number.')
      }
      filters.patient_nbr = Number(patient)
    }
    if (riskLevel) filters.risk_level = riskLevel
    if (score) {
      if (!/^\d+$/.test(score) || Number(score) > 8) {
        return setFormError('Risk Score must be a whole number from 0 to 8.')
      }
      filters.risk_score = Number(score)
    }
    if (Object.keys(filters).length === 0) {
      return setFormError('Enter a Patient Number, Risk Level or Risk Score.')
    }
    setFormError(null)

    setLoading(true)
    try {
      setResults(await searchEncounters(filters, RESULT_LIMIT))
    } catch (err) {
      setResults(null)
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setPatientNbr('')
    setRiskLevel('')
    setRiskScore('')
    setFormError(null)
    setError(null)
    setResults(null)
  }

  return (
    <section className="card">
      <header className="card-header">
        <span className="card-icon">
          <SearchIcon />
        </span>
        <div>
          <h2>Search Patient</h2>
          <p>Filter by any combination of patient number, risk level and risk score.</p>
        </div>
      </header>

      <form className="form" onSubmit={handleSubmit} noValidate>
        <div className="form-grid three">
          <Field label="Patient Number">
            <input
              inputMode="numeric"
              value={patientNbr}
              onChange={(event) => setPatientNbr(event.target.value)}
              placeholder="Any"
            />
          </Field>
          <Field label="Risk Level">
            <select
              value={riskLevel}
              onChange={(event) => setRiskLevel(event.target.value as RiskLevel | '')}
            >
              <option value="">Any</option>
              {RISK_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Risk Score" hint="0 – 8">
            <input
              type="number"
              min={0}
              max={8}
              step={1}
              value={riskScore}
              onChange={(event) => setRiskScore(event.target.value)}
              placeholder="Any"
            />
          </Field>
        </div>

        {formError && <Alert kind="error">{formError}</Alert>}
        {error && <Alert kind="error">{error}</Alert>}

        <div className="form-actions">
          <button type="button" className="button ghost" onClick={handleClear}>
            Clear
          </button>
          <button type="submit" className="button primary" disabled={loading}>
            {loading ? 'Searching…' : 'Search'}
            <ChevronRightIcon />
          </button>
        </div>
      </form>

      {results && (
        <div className="results">
          <div className="results-meta">
            {results.length === RESULT_LIMIT
              ? `Showing the first ${RESULT_LIMIT} matches, highest risk first`
              : `${results.length} encounter${results.length === 1 ? '' : 's'} found`}
          </div>
          {results.length === 0 ? (
            <EmptyState>
              <InboxIcon size={28} />
              No encounters match these filters.
            </EmptyState>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Encounter</th>
                    <th>Patient</th>
                    <th>Age</th>
                    <th className="num">Days</th>
                    <th className="num">Inpatient</th>
                    <th className="num">Emergency</th>
                    <th className="num">Meds</th>
                    <th>Risk</th>
                    <th>Care status</th>
                    <th>Assigned to</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((row) => (
                    <tr key={row.encounter_id}>
                      <td>
                        {row.status ? (
                          <a href={statusHref(row.encounter_id)} title="Open in status tracking">
                            {row.encounter_id}
                          </a>
                        ) : (
                          row.encounter_id
                        )}
                      </td>
                      <td>{row.patient_nbr}</td>
                      <td>{row.age}</td>
                      <td className="num">{row.time_in_hospital}</td>
                      <td className="num">{row.number_inpatient}</td>
                      <td className="num">{row.number_emergency}</td>
                      <td className="num">{row.num_medications}</td>
                      <td>
                        <RiskBadge level={row.risk_level} score={row.risk_score} />
                      </td>
                      <td>
                        <StatusBadge status={row.status} />
                      </td>
                      <td className="muted">{row.assigned_to ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
