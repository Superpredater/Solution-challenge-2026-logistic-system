import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import {
  ArrowLeft,
  Plane,
  Ship,
  Train,
  Truck,
  CheckCircle,
  XCircle,
  Bot,
  AlertTriangle,
  Clock,
  Leaf,
  DollarSign,
} from 'lucide-react'
import {
  getShipment,
  getShipmentRecommendations,
  getShipmentRiskHistory,
  getShipmentAIExplanation,
  acceptRecommendation,
  rejectRecommendation,
  getShipmentRoute,
} from '../api/shipments'
import { RiskBadge } from '../components/ui/RiskBadge'
import { RiskGauge } from '../components/charts/RiskGauge'
import { RiskTrendChart } from '../components/charts/RiskTrendChart'
import { PageLoader } from '../components/ui/LoadingSpinner'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { useUIStore } from '../store/uiStore'
import { useAuthStore } from '../store/authStore'
import type { RerouteRecommendation, TransportMode } from '../types'

const MODE_ICONS: Record<TransportMode, React.ReactNode> = {
  air: <Plane size={14} />,
  sea: <Ship size={14} />,
  rail: <Train size={14} />,
  road: <Truck size={14} />,
}

const MODE_LABELS: Record<TransportMode, string> = {
  air: 'Air',
  sea: 'Sea',
  rail: 'Rail',
  road: 'Road',
}

export default function ShipmentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)
  const hasRole = useAuthStore((s) => s.hasRole)

  const [confirmRec, setConfirmRec] = useState<{
    rec: RerouteRecommendation
    action: 'accept' | 'reject'
  } | null>(null)

  const { data: shipment, isLoading } = useQuery({
    queryKey: ['shipment', id],
    queryFn: () => getShipment(id!),
    enabled: !!id,
    refetchInterval: 30_000,
  })

  const { data: route } = useQuery({
    queryKey: ['shipment-route', id],
    queryFn: () => getShipmentRoute(id!),
    enabled: !!id,
  })

  const { data: recommendations } = useQuery({
    queryKey: ['recommendations', id],
    queryFn: () => getShipmentRecommendations(id!),
    enabled: !!id,
  })

  const { data: riskHistory } = useQuery({
    queryKey: ['risk-history', id],
    queryFn: () => getShipmentRiskHistory(id!, 48),
    enabled: !!id,
  })

  const { data: aiExplanation } = useQuery({
    queryKey: ['ai-explanation', id],
    queryFn: () => getShipmentAIExplanation(id!),
    enabled: !!id,
  })

  const acceptMutation = useMutation({
    mutationFn: ({ recId, notes }: { recId: string; notes?: string }) =>
      acceptRecommendation(id!, recId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipment', id] })
      queryClient.invalidateQueries({ queryKey: ['recommendations', id] })
      addToast({ type: 'success', title: 'Route updated', message: 'Reroute recommendation accepted' })
      setConfirmRec(null)
    },
    onError: () => {
      addToast({ type: 'error', title: 'Failed to accept recommendation' })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ recId }: { recId: string }) => rejectRecommendation(id!, recId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations', id] })
      addToast({ type: 'info', title: 'Recommendation rejected' })
      setConfirmRec(null)
    },
    onError: () => {
      addToast({ type: 'error', title: 'Failed to reject recommendation' })
    },
  })

  if (isLoading) return <PageLoader />
  if (!shipment) return (
    <div className="flex flex-col items-center justify-center h-64 gap-4">
      <AlertTriangle size={40} className="text-accent-amber" />
      <p className="text-text-secondary">Shipment not found</p>
      <button onClick={() => navigate('/shipments')} className="btn-secondary">Back to Shipments</button>
    </div>
  )

  const pendingRecs = recommendations?.filter((r) => r.status === 'pending') || []

  // Risk dimension breakdown from latest history event
  const latestRisk = riskHistory?.[riskHistory.length - 1]
  const dimensions = latestRisk
    ? [
        { label: 'Weather', value: latestRisk.weather_component, color: '#3b82f6' },
        { label: 'Operational', value: latestRisk.operational_component, color: '#f59e0b' },
        { label: 'War State', value: latestRisk.war_state_component, color: '#ef4444' },
        { label: 'Geopolitical', value: latestRisk.geopolitical_component, color: '#f97316' },
      ]
    : []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => navigate('/shipments')}
          className="p-2 rounded-lg hover:bg-surface transition-colors text-text-secondary mt-0.5"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-text-primary text-xl font-bold font-mono">
              {shipment.shipment_id.slice(0, 8).toUpperCase()}
            </h1>
            <span
              className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                shipment.status === 'Delayed'
                  ? 'bg-accent-red/20 text-accent-red'
                  : shipment.status === 'In_Transit'
                  ? 'bg-accent-blue/20 text-accent-blue'
                  : shipment.status === 'Connectivity_Impaired'
                  ? 'bg-accent-amber/20 text-accent-amber'
                  : 'bg-accent-green/20 text-accent-green'
              }`}
            >
              {shipment.status.replace(/_/g, ' ')}
            </span>
            <RiskBadge score={shipment.risk_score} showLabel />
          </div>
          <p className="text-text-secondary text-sm mt-1">
            {shipment.origin.name} → {shipment.destination.name}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="xl:col-span-2 space-y-6">
          {/* ETA + Risk Gauge */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card flex flex-col items-center justify-center py-6">
              <RiskGauge score={shipment.risk_score} size={160} />
            </div>
            <div className="card space-y-4">
              <div>
                <p className="text-text-secondary text-xs uppercase tracking-wide mb-1">ETA</p>
                <p className="text-text-primary text-xl font-bold">
                  {format(parseISO(shipment.eta), 'MMM d, yyyy HH:mm')}
                </p>
                {shipment.eta_confidence_interval && (
                  <p className="text-text-muted text-xs mt-1">
                    Confidence: {format(parseISO(shipment.eta_confidence_interval[0]), 'HH:mm')} –{' '}
                    {format(parseISO(shipment.eta_confidence_interval[1]), 'HH:mm')}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-surface rounded-lg p-3">
                  <p className="text-text-muted text-xs mb-1">Carbon</p>
                  <p className="text-text-primary font-semibold text-sm">
                    {shipment.carbon_kg.toFixed(0)} kg CO₂
                  </p>
                </div>
                <div className="bg-surface rounded-lg p-3">
                  <p className="text-text-muted text-xs mb-1">Priority</p>
                  <p
                    className={`font-semibold text-sm ${
                      shipment.demand_priority === 'High'
                        ? 'text-accent-red'
                        : shipment.demand_priority === 'Elevated'
                        ? 'text-accent-amber'
                        : 'text-text-primary'
                    }`}
                  >
                    {shipment.demand_priority}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Route Legs */}
          {route && route.legs.length > 0 && (
            <div className="card">
              <h2 className="text-text-primary font-semibold mb-4">Active Route</h2>
              <div className="space-y-2">
                {route.legs.map((leg, i) => (
                  <div
                    key={leg.leg_id}
                    className="flex items-center gap-3 p-3 bg-surface rounded-lg"
                  >
                    <span className="w-6 h-6 rounded-full bg-accent-blue/20 text-accent-blue text-xs font-bold flex items-center justify-center shrink-0">
                      {i + 1}
                    </span>
                    <span className="text-accent-blue shrink-0">{MODE_ICONS[leg.transport_mode]}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-text-primary text-sm font-medium truncate">
                        {leg.origin_name || leg.origin_node_id.slice(0, 8)} →{' '}
                        {leg.destination_name || leg.destination_node_id.slice(0, 8)}
                      </p>
                      <p className="text-text-muted text-xs">{MODE_LABELS[leg.transport_mode]}</p>
                    </div>
                    <div className="text-right shrink-0 space-y-0.5">
                      <div className="flex items-center gap-1 text-text-secondary text-xs">
                        <Clock size={11} />
                        {leg.estimated_duration_hours.toFixed(1)}h
                      </div>
                      <div className="flex items-center gap-1 text-text-secondary text-xs">
                        <DollarSign size={11} />
                        {leg.estimated_cost_usd.toFixed(0)}
                      </div>
                      <div className="flex items-center gap-1 text-text-secondary text-xs">
                        <Leaf size={11} />
                        {leg.carbon_kg.toFixed(0)}kg
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3 pt-3 border-t border-border flex gap-6 text-sm">
                <span className="text-text-secondary">
                  Total: <span className="text-text-primary font-medium">{route.total_distance_km.toFixed(0)} km</span>
                </span>
                <span className="text-text-secondary">
                  Cost: <span className="text-text-primary font-medium">${route.total_estimated_cost_usd.toFixed(0)}</span>
                </span>
                <span className="text-text-secondary">
                  CO₂: <span className="text-text-primary font-medium">{route.total_carbon_kg.toFixed(0)} kg</span>
                </span>
              </div>
            </div>
          )}

          {/* Risk Breakdown */}
          {dimensions.length > 0 && (
            <div className="card">
              <h2 className="text-text-primary font-semibold mb-4">Risk Score Breakdown</h2>
              <div className="space-y-3">
                {dimensions.map((dim) => (
                  <div key={dim.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-text-secondary">{dim.label}</span>
                      <span className="text-text-primary font-medium">{dim.value.toFixed(1)}</span>
                    </div>
                    <div className="h-2 bg-surface rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min(100, (dim.value / 100) * 100)}%`,
                          backgroundColor: dim.color,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Risk History Chart */}
          {riskHistory && riskHistory.length > 0 && (
            <div className="card">
              <h2 className="text-text-primary font-semibold mb-4">Risk Score History (48h)</h2>
              <RiskTrendChart data={riskHistory} height={200} />
            </div>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* AI Explanation */}
          <div className="card">
            <div className="flex items-center gap-2 mb-3">
              <Bot size={16} className="text-accent-blue" />
              <h2 className="text-text-primary font-semibold">AI Risk Explanation</h2>
              {aiExplanation?.fallback_used && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-accent-amber/20 text-accent-amber ml-auto">
                  Fallback
                </span>
              )}
            </div>
            {aiExplanation ? (
              <p className="text-text-secondary text-sm leading-relaxed">{aiExplanation.explanation}</p>
            ) : (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-3 bg-surface rounded animate-pulse" style={{ width: `${90 - i * 10}%` }} />
                ))}
              </div>
            )}
          </div>

          {/* Reroute Recommendations */}
          {pendingRecs.length > 0 && (
            <div className="card">
              <h2 className="text-text-primary font-semibold mb-4">
                Reroute Recommendations
                <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-accent-amber/20 text-accent-amber">
                  {pendingRecs.length}
                </span>
              </h2>
              <div className="space-y-3">
                {pendingRecs.map((rec, i) => (
                  <div key={rec.recommendation_id} className="bg-surface rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-text-secondary text-xs">Option {i + 1}</span>
                      <span className="text-xs text-accent-blue font-medium">
                        Score: {rec.rank_score.toFixed(1)}
                      </span>
                    </div>
                    <p className="text-text-primary text-sm font-medium">
                      New ETA: {format(parseISO(rec.new_eta), 'MMM d, HH:mm')}
                    </p>
                    <div className="flex gap-3 text-xs">
                      <span className={rec.cost_delta_usd >= 0 ? 'text-accent-red' : 'text-accent-green'}>
                        {rec.cost_delta_usd >= 0 ? '+' : ''}${rec.cost_delta_usd.toFixed(0)} cost
                      </span>
                      <span className={rec.carbon_delta_kg >= 0 ? 'text-accent-red' : 'text-accent-green'}>
                        {rec.carbon_delta_kg >= 0 ? '+' : ''}{rec.carbon_delta_kg.toFixed(0)} kg CO₂
                      </span>
                    </div>
                    {hasRole('Manager') && (
                      <div className="flex gap-2 pt-1">
                        <button
                          onClick={() => setConfirmRec({ rec, action: 'accept' })}
                          className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-accent-green/20 text-accent-green text-xs font-medium hover:bg-accent-green/30 transition-colors"
                        >
                          <CheckCircle size={12} />
                          Accept
                        </button>
                        <button
                          onClick={() => setConfirmRec({ rec, action: 'reject' })}
                          className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-accent-red/20 text-accent-red text-xs font-medium hover:bg-accent-red/30 transition-colors"
                        >
                          <XCircle size={12} />
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Shipment Info */}
          <div className="card">
            <h2 className="text-text-primary font-semibold mb-3">Details</h2>
            <dl className="space-y-2 text-sm">
              {[
                { label: 'Shipment ID', value: shipment.shipment_id },
                { label: 'Carrier', value: shipment.carrier_name || shipment.carrier_id.slice(0, 8) },
                { label: 'Updated', value: format(parseISO(shipment.risk_score_updated_at), 'MMM d, HH:mm') },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between gap-2">
                  <dt className="text-text-muted">{label}</dt>
                  <dd className="text-text-primary font-medium text-right truncate max-w-[60%] font-mono text-xs">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>

      {/* Confirm Dialog */}
      {confirmRec && (
        <ConfirmDialog
          title={confirmRec.action === 'accept' ? 'Accept Reroute?' : 'Reject Recommendation?'}
          message={
            confirmRec.action === 'accept'
              ? `This will update the active route and recalculate the ETA. New ETA: ${format(parseISO(confirmRec.rec.new_eta), 'MMM d, HH:mm')}`
              : 'This recommendation will be marked as rejected.'
          }
          confirmLabel={confirmRec.action === 'accept' ? 'Accept Route' : 'Reject'}
          variant={confirmRec.action === 'reject' ? 'danger' : 'primary'}
          onConfirm={() => {
            if (confirmRec.action === 'accept') {
              acceptMutation.mutate({ recId: confirmRec.rec.recommendation_id })
            } else {
              rejectMutation.mutate({ recId: confirmRec.rec.recommendation_id })
            }
          }}
          onCancel={() => setConfirmRec(null)}
        />
      )}
    </div>
  )
}
