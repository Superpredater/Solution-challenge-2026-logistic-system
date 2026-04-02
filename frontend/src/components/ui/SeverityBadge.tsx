import clsx from 'clsx'
import type { AlertSeverity, DisruptionSeverity } from '../../types'

type Severity = AlertSeverity | DisruptionSeverity

const SEVERITY_STYLES: Record<string, string> = {
  Critical: 'bg-accent-red/20 text-accent-red',
  High: 'bg-accent-red/20 text-accent-red',
  Warning: 'bg-accent-amber/20 text-accent-amber',
  Medium: 'bg-accent-amber/20 text-accent-amber',
  Informational: 'bg-accent-blue/20 text-accent-blue',
  Low: 'bg-text-muted/20 text-text-secondary',
}

interface SeverityBadgeProps {
  severity: Severity
  size?: 'sm' | 'md'
}

export function SeverityBadge({ severity, size = 'md' }: SeverityBadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full font-medium',
        SEVERITY_STYLES[severity] || 'bg-surface text-text-secondary',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'
      )}
    >
      {severity}
    </span>
  )
}
