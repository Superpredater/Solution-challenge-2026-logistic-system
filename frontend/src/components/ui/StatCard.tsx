import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: LucideIcon
  iconColor?: string
  trend?: { value: number; label: string }
  loading?: boolean
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconColor = 'text-accent-blue',
  trend,
  loading = false,
}: StatCardProps) {
  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="h-4 bg-border rounded w-24 mb-3" />
        <div className="h-8 bg-border rounded w-16 mb-2" />
        <div className="h-3 bg-border rounded w-20" />
      </div>
    )
  }

  return (
    <div className="card flex items-start gap-4">
      <div className={clsx('p-2.5 rounded-lg bg-surface', iconColor)}>
        <Icon size={20} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-text-secondary text-sm">{title}</p>
        <p className="text-2xl font-bold text-text-primary mt-0.5">{value}</p>
        {subtitle && <p className="text-text-muted text-xs mt-0.5">{subtitle}</p>}
        {trend && (
          <p
            className={clsx(
              'text-xs mt-1 font-medium',
              trend.value >= 0 ? 'text-accent-red' : 'text-accent-green'
            )}
          >
            {trend.value >= 0 ? '↑' : '↓'} {Math.abs(trend.value)}% {trend.label}
          </p>
        )}
      </div>
    </div>
  )
}
