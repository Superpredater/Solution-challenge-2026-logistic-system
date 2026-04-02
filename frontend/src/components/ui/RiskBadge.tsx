import clsx from 'clsx'
import { useRiskColor } from '../../hooks/useRiskColor'

interface RiskBadgeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
}

export function RiskBadge({ score, size = 'md', showLabel = false }: RiskBadgeProps) {
  const { getRiskBgClass, getRiskLabel } = useRiskColor()

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full font-semibold tabular-nums',
        getRiskBgClass(score),
        {
          'px-2 py-0.5 text-xs': size === 'sm',
          'px-2.5 py-1 text-sm': size === 'md',
          'px-3 py-1.5 text-base': size === 'lg',
        }
      )}
    >
      {score.toFixed(1)}
      {showLabel && <span className="opacity-75">· {getRiskLabel(score)}</span>}
    </span>
  )
}
