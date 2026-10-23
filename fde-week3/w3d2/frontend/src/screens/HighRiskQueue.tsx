import { useEffect, useState } from 'react'
import { getHighRiskQueue, type CareQueueItem } from '../api'
import { Alert, EmptyState } from '../components/Alert'
import { RiskBadge, StatusBadge } from '../components/Badges'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  InboxIcon,
  RefreshIcon,
  ShieldAlertIcon,
} from '../components/Icons'
import { statusHref } from '../routes'

const PAGE_SIZE = 25

export function HighRiskQueue() {
  const [page, setPage] = useState(0)
  const [reloadKey, setReloadKey] = useState(0)
  const [rows, setRows] = useState<CareQueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const startLoading = () => {
    setLoading(true)
    setError(null)
  }

  useEffect(() => {
    let cancelled = false
    getHighRiskQueue(PAGE_SIZE, page * PAGE_SIZE)
      .then((data) => !cancelled && setRows(data))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : String(err)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [page, reloadKey])

  return (
    <section className="card">
      <header className="card-header">
        <span className="card-icon danger">
          <ShieldAlertIcon />
        </span>
        <div>
          <h2>High-Risk Care Queue</h2>
          <p>HIGH risk encounters, highest score first. Select an encounter to update its care status.</p>
        </div>
        <button
          type="button"
          className="button ghost icon-only"
          onClick={() => {
            startLoading()
            setReloadKey((key) => key + 1)
          }}
          title="Refresh"
          aria-label="Refresh"
        >
          <RefreshIcon />
        </button>
      </header>

      {error && <Alert kind="error">{error}</Alert>}

      {!error && !loading && rows.length === 0 ? (
        <EmptyState>
          <InboxIcon size={28} />
          {page === 0 ? 'No high-risk encounters in the queue.' : 'No more encounters.'}
        </EmptyState>
      ) : (
        !error && (
          <div className={`table-wrap${loading ? ' is-loading' : ''}`}>
            <table>
              <thead>
                <tr>
                  <th>Encounter</th>
                  <th>Patient</th>
                  <th>Age</th>
                  <th className="num">Inpatient</th>
                  <th className="num">Emergency</th>
                  <th className="num">Days</th>
                  <th>Risk</th>
                  <th>Care status</th>
                  <th>Assigned to</th>
                  <th>Last updated</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.encounter_id}>
                    <td>
                      <a href={statusHref(row.encounter_id)} title="Update care status">
                        {row.encounter_id}
                      </a>
                    </td>
                    <td>{row.patient_nbr}</td>
                    <td>{row.age}</td>
                    <td className="num">{row.number_inpatient}</td>
                    <td className="num">{row.number_emergency}</td>
                    <td className="num">{row.time_in_hospital}</td>
                    <td>
                      <RiskBadge level={row.risk_level} score={row.risk_score} />
                    </td>
                    <td>
                      <StatusBadge status={row.status} />
                    </td>
                    <td className="muted">{row.assigned_to ?? '—'}</td>
                    <td className="muted">{new Date(row.updated_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      <div className="pager">
        <button
          type="button"
          className="button ghost"
          disabled={page === 0 || loading}
          onClick={() => {
            startLoading()
            setPage((current) => current - 1)
          }}
        >
          <ChevronLeftIcon /> Previous
        </button>
        <span className="muted">Page {page + 1}</span>
        <button
          type="button"
          className="button ghost"
          disabled={rows.length < PAGE_SIZE || loading}
          onClick={() => {
            startLoading()
            setPage((current) => current + 1)
          }}
        >
          Next <ChevronRightIcon />
        </button>
      </div>
    </section>
  )
}
