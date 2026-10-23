import type { InterventionStatus } from './api'

const STATUS_LABELS: Record<InterventionStatus, string> = {
  PENDING_REVIEW: 'Pending review',
  ASSIGNED: 'Assigned',
  CONTACTED: 'Contacted',
  FOLLOW_UP_SCHEDULED: 'Follow-up scheduled',
  CLOSED: 'Closed',
}

export function statusLabel(status: InterventionStatus): string {
  return STATUS_LABELS[status]
}
