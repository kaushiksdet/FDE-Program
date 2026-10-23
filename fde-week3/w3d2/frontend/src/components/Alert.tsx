import type { ReactNode } from 'react'
import { AlertCircleIcon, CheckCircleIcon } from './Icons'

export function Alert({ kind, children }: { kind: 'error' | 'success'; children: ReactNode }) {
  return (
    <div className={`alert alert-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      {kind === 'error' ? <AlertCircleIcon /> : <CheckCircleIcon />}
      <div>{children}</div>
    </div>
  )
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>
}
