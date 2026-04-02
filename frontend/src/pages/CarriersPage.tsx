import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { X, TrendingUp, AlertTriangle } from 'lucide-react'
import { getCarriers, getCarrierRiskHistory } from '../api/carriers'
import { DataTable } from '../components/ui/DataTable'
import { RiskBadge } from '../components/ui/RiskBadge'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format, parseISO } from 'date-fns'
import type { CarrierProfile, Column } from '../types'

function CarrierDetailModal({
  carrier,
  onClose,
}: {
  carrier: CarrierProfile
  onClose: () => void
}) {
  const { data: history } = useQuery({
    queryKey: ['carrier-risk-history', carrier.carrier_id],
    queryFn: () => getCarrierRiskHistory(carrier.carrier_id),
  })

  const chartData = (history || []).map((h) => ({
    time: format(parseISO(h.recorded_at), 'MMM d'),
    risk: h.risk_score,
  }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-card border border-border rounded-2xl w-full max-w-2xl shadow-2xl">
        <div className="flex items-start justify-between p-6 border-b border-border">
          <div>
            <h2 className="text-text-primary font-semibold text-lg">{carrier.name}</h2>
            <p className="text-text-muted text-xs font-mono mt-0.5">{carrier.carrier_id}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface transition-colors text-text-muted"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Stats grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: '90d On-Time', value: `${(carrier.on_time_rate_90d * 100).toFixed(1)}%` },
              { label: '30d On-Time', value: `${(carrier.on_time_rate_30d * 100).toFixed(1)}%` },
              { label: 'Incidents (90d)', value: carrier.incident_count_90d },
              { label: 'Capacity Score', value: `${(carrier.capacity_reliability_score * 100).toFixed(0)}%` },
            ].map(({ label, value }) => (
              <div key={label} className="bg-surface rounded-lg p-3 text-center">
                <p className="text-text-muted text-xs mb-1">{label}</p>
                <p className="text-text-primary font-bold text-lg">{value}</p>
              </div>
            ))}
          </div>

          {/* Risk score */}
          <div className="flex items-center gap-3">
            <span className="text-text-secondary text-sm">Risk Score:</span>
            <RiskBadge score={carrier.risk_score} showLabel />
            {carrier.is_high_risk && (
              <span className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-accent-red/20 text-accent-red font-medium">
                <AlertTriangle size={12} />
                High Risk Carrier
              </span>
            )}
          </div>

          {/* Trend chart */}
          {chartData.length > 0 && (
            <div>
              <p className="text-text-secondary text-sm font-medium mb-3">Risk Score Trend</p>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                  <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#1e2235', border: '1px solid #2a2d3e', borderRadius: 8 }}
                    labelStyle={{ color: '#94a3b8' }}
                    itemStyle={{ color: '#f1f5f9' }}
                  />
                  <Line type="monotone" dataKey="risk" stroke="#3b82f6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function CarriersPage() {
  const [selectedCarrier, setSelectedCarrier] = useState<CarrierProfile | null>(null)

  const { data: carriers, isLoading } = useQuery({
    queryKey: ['carriers'],
    queryFn: getCarriers,
    refetchInterval: 60_000,
  })

  const columns: Column<CarrierProfile>[] = [
    {
      key: 'name',
      header: 'Carrier',
      render: (c) => (
        <div>
          <p className="text-text-primary font-medium text-sm">{c.name}</p>
          {c.is_high_risk && (
            <span className="text-xs text-accent-red flex items-center gap-1 mt-0.5">
              <AlertTriangle size={10} />
              High Risk
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'on_time_90d',
      header: '90d On-Time',
      render: (c) => (
        <span
          className={`text-sm font-medium ${
            c.on_time_rate_90d >= 0.9
              ? 'text-accent-green'
              : c.on_time_rate_90d >= 0.8
              ? 'text-accent-amber'
              : 'text-accent-red'
          }`}
        >
          {(c.on_time_rate_90d * 100).toFixed(1)}%
        </span>
      ),
    },
    {
      key: 'on_time_30d',
      header: '30d On-Time',
      render: (c) => (
        <span
          className={`text-sm font-medium ${
            c.on_time_rate_30d >= 0.9
              ? 'text-accent-green'
              : c.on_time_rate_30d >= 0.8
              ? 'text-accent-amber'
              : 'text-accent-red'
          }`}
        >
          {(c.on_time_rate_30d * 100).toFixed(1)}%
        </span>
      ),
    },
    {
      key: 'incidents',
      header: 'Incidents (90d)',
      render: (c) => (
        <span className={`text-sm ${c.incident_count_90d > 5 ? 'text-accent-red' : 'text-text-primary'}`}>
          {c.incident_count_90d}
        </span>
      ),
    },
    {
      key: 'risk',
      header: 'Risk Score',
      render: (c) => <RiskBadge score={c.risk_score} size="sm" />,
    },
    {
      key: 'updated',
      header: 'Updated',
      render: (c) => (
        <span className="text-text-muted text-xs">
          {c.profile_updated_at ? format(parseISO(c.profile_updated_at), 'MMM d') : '—'}
        </span>
      ),
    },
  ]

  const highRiskCount = (carriers || []).filter((c) => c.is_high_risk).length

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-text-primary text-2xl font-bold">Carriers</h1>
          <p className="text-text-secondary text-sm mt-0.5">
            {carriers?.length || '—'} carriers tracked
            {highRiskCount > 0 && (
              <span className="ml-2 text-accent-red">· {highRiskCount} high risk</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <TrendingUp size={14} />
          Rolling 90-day window
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <DataTable
          columns={columns}
          data={carriers || []}
          loading={isLoading}
          onRowClick={setSelectedCarrier}
          keyExtractor={(c) => c.carrier_id}
          emptyTitle="No carriers found"
          emptyDescription="Carrier profiles will appear once data is available"
        />
      </div>

      {selectedCarrier && (
        <CarrierDetailModal carrier={selectedCarrier} onClose={() => setSelectedCarrier(null)} />
      )}
    </div>
  )
}
