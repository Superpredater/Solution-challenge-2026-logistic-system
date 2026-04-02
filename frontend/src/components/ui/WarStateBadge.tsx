import clsx from 'clsx'
import type { WarState } from '../../types'

const WAR_STATE_STYLES: Record<WarState, string> = {
  Safe: 'bg-accent-green/20 text-accent-green',
  Caution: 'bg-accent-yellow/20 text-accent-yellow',
  High_Risk: 'bg-accent-orange/20 text-accent-orange',
  Restricted: 'bg-accent-red/20 text-accent-red',
}

interface WarStateBadgeProps {
  warState: WarState
  size?: 'sm' | 'md'
}

export function WarStateBadge({ warState, size = 'md' }: WarStateBadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full font-medium',
        WAR_STATE_STYLES[warState],
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'
      )}
    >
      {warState.replace('_', ' ')}
    </span>
  )
}
