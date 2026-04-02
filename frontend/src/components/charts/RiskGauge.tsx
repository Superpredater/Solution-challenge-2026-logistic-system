import { useRiskColor } from '../../hooks/useRiskColor'

interface RiskGaugeProps {
  score: number
  size?: number
}

export function RiskGauge({ score, size = 120 }: RiskGaugeProps) {
  const { getRiskColor, getRiskLabel } = useRiskColor()
  const color = getRiskColor(score)
  const label = getRiskLabel(score)

  const radius = (size - 16) / 2
  const circumference = Math.PI * radius // half circle
  const strokeDashoffset = circumference - (score / 100) * circumference

  const cx = size / 2
  const cy = size / 2 + 10

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size * 0.65} viewBox={`0 0 ${size} ${size * 0.65}`}>
        {/* Background arc */}
        <path
          d={`M ${16} ${cy} A ${radius} ${radius} 0 0 1 ${size - 16} ${cy}`}
          fill="none"
          stroke="#2a2d3e"
          strokeWidth={10}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={`M ${16} ${cy} A ${radius} ${radius} 0 0 1 ${size - 16} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          style={{ transition: 'stroke-dashoffset 0.5s ease' }}
        />
        {/* Score text */}
        <text
          x={cx}
          y={cy - 4}
          textAnchor="middle"
          fill="white"
          fontSize={size * 0.22}
          fontWeight="700"
          fontFamily="Inter, sans-serif"
        >
          {score.toFixed(0)}
        </text>
        <text
          x={cx}
          y={cy + size * 0.12}
          textAnchor="middle"
          fill={color}
          fontSize={size * 0.1}
          fontWeight="600"
          fontFamily="Inter, sans-serif"
        >
          {label} Risk
        </text>
      </svg>
    </div>
  )
}
