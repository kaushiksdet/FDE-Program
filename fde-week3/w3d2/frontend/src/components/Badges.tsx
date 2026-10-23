import type { InterventionStatus, RiskLevel } from '../api'
import { statusLabel } from '../labels'

export function RiskBadge({ level, score }: { level: RiskLevel; score?: number }) {
  return (
    <span className={`badge risk-${level.toLowerCase()}`}>
      {level}
      {score !== undefined && <span className="badge-score">{score}</span>}
    </span>
  )
}

export function StatusBadge({ status }: { status: InterventionStatus | null }) {
  if (status === null) return <span className="badge status-none">Not in queue</span>
  return (
    <span className={`badge status-${status.toLowerCase().replaceAll('_', '-')}`}>
      {statusLabel(status)}
    </span>
  )
}
