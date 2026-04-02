export function useRiskColor() {
  const getRiskColor = (score: number): string => {
    if (score >= 70) return '#ef4444'   // red
    if (score >= 40) return '#f59e0b'   // amber
    return '#22c55e'                     // green
  }

  const getRiskBgClass = (score: number): string => {
    if (score >= 70) return 'bg-accent-red/20 text-accent-red'
    if (score >= 40) return 'bg-accent-amber/20 text-accent-amber'
    return 'bg-accent-green/20 text-accent-green'
  }

  const getRiskLabel = (score: number): string => {
    if (score >= 70) return 'High'
    if (score >= 40) return 'Medium'
    return 'Low'
  }

  const getRiskTextClass = (score: number): string => {
    if (score >= 70) return 'text-accent-red'
    if (score >= 40) return 'text-accent-amber'
    return 'text-accent-green'
  }

  return { getRiskColor, getRiskBgClass, getRiskLabel, getRiskTextClass }
}
