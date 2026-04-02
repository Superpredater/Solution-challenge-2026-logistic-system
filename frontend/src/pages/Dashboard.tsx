import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Package, AlertTriangle, Bell, TrendingUp, Map, Cpu, Bot } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { getShipments } from '../api/shipments'
import { getAlerts } from '../api/alerts'
import { StatCard } from '../components/ui/StatCard'
import { RiskBadge } from '../components/ui/RiskBadge'
import { SeverityBadge } from '../components/ui/SeverityBadge'
import { RiskTrendChart } from '../components/charts/RiskTrendChart'
import { DataTable } from '../components/ui/DataTable'
import type { Shipment, Alert, Column } from '../types'

export default function Dashboard() {
  const navigate = useNavigate()

  const { data: shipmentsData, isLoading: shipmentsLoading } = useQuery({
    queryKey: ['shipments', { page: 1, page_size: 10 }],
    queryFn: () => getShipments({ page: 1, page_size: 10 }),
    refetchInterval: 30_000,
  })

  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: ['alerts', { severity: 'Critical', page: 1, page_size: 20 }],
    queryFn: () => getAlerts({ page: 1, page_size: 20 }),
    refetchInterval: 15_000,
  })

  const shipments = shipmentsData?.items || []
  const alerts = alertsData?.items || []

  const highRiskCount = shipments.filter((s) => s.risk_score >= 70).length
  const avgRisk = shipments.length
    ? (shipments.reduce((sum, s) => sum + s.risk_score, 0) / shipments.length).toFixed(1)
    : '0.0'
  const criticalAlerts = alerts.filter((a) => a.severity === 'Critical').length

  // Build mock risk trend from shipments for demo
  const riskTrendData = shipments.slice(0, 10).map((s, i) => ({
    event_id: s.shipment_id,
    shipment_id: s.shipment_id,
    tenant_id: s.tenant_id,
    risk_score: s.risk_score,
    weather_component: s.risk_score * 0.25,
    operational_component: s.risk_score * 0.30,
    war_state_component: s.risk_score * 0.25,
    geopolitical_component: s.risk_score * 0.20,
    recorded_at: new Date(Date.now() - (10 - i) * 3600_000).toISOString(),
  }))

  const shipmentColumns: Column<Shipment>[] = [
    {
      key: 'id',
      header: 'Shipment ID',
      render: (s) => (
        <span className="font-mono text-xs text-accent-blue">
          {s.shipment_id.slice(0, 8)}...
        </span>
      ),
    },
    {
      key: 'route',
      header: 'Route',
      render: (s) => (
        <span className="text-text-primary text-xs">
          {s.origin.name} → {s.destination.name}
        </span>
      ),
    },
    {
      key: 'carrier',
      header: 'Carrier',
      render: (s) => (
        <span className="text-text-secondary text-xs">{s.carrier_name || s.carrier_id.slice(0, 8)}</span>
      ),
    },
    {
      key: 'risk',
      header: 'Risk Score',
      render: (s) => <RiskBadge score={s.risk_score} size="sm" />,
    },
    {
      key: 'eta',
      header: 'ETA',
      render: (s) => (
        <span className="text-text-secondary text-xs">
          {s.eta ? format(parseISO(s.eta), 'MMM d, HH:mm') : '—'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (s) => (
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            s.status === 'Delayed'
              ? 'bg-accent-red/20 text-accent-red'
              : s.status === 'In_Transit'
              ? 'bg-accent-blue/20 text-accent-blue'
              : 'bg-accent-green/20 text-accent-green'
          }`}
        >
          {s.status.replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (s) => (
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            s.demand_priority === 'High'
              ? 'bg-accent-red/20 text-accent-red'
              : s.demand_priority === 'Elevated'
              ? 'bg-accent-amber/20 text-accent-amber'
              : 'bg-surface text-text-muted'
          }`}
        >
          {s.demand_priority}
        </span>
      ),
    },
  ]

  const alertColumns: Column<Alert>[] = [
    {
      key: 'severity',
      header: 'Severity',
      render: (a) => <SeverityBadge severity={a.severity} size="sm" />,
    },
    {
      key: 'message',
      header: 'Message',
      render: (a) => (
        <span className="text-text-primary text-xs line-clamp-1">{a.message}</span>
      ),
    },
    {
      key: 'time',
      header: 'Time',
      render: (a) => (
        <span className="text-text-muted text-xs whitespace-nowrap">
          {a.created_at ? format(parseISO(a.created_at), 'HH:mm') : '—'}
        </span>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-text-primary text-2xl font-bold">Dashboard</h1>
        <p className="text-text-secondary text-sm mt-0.5">
          Real-time supply chain intelligence overview
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Shipments"
          value={shipmentsData?.total?.toLocaleString() || '—'}
          icon={Package}
          iconColor="text-accent-blue"
          loading={shipmentsLoading}
        />
        <StatCard
          title="High Risk Shipments"
          value={highRiskCount}
          subtitle="Risk score > 70"
          icon={AlertTriangle}
          iconColor="text-accent-red"
          loading={shipmentsLoading}
        />
        <StatCard
          title="Critical Alerts"
          value={criticalAlerts}
          subtitle="Requires attention"
          icon={Bell}
          iconColor="text-accent-amber"
          loading={alertsLoading}
        />
        <StatCard
          title="Avg Risk Score"
          value={avgRisk}
          subtitle="Across active shipments"
          icon={TrendingUp}
          iconColor="text-accent-green"
          loading={shipmentsLoading}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Risk Trend */}
        <div className="xl:col-span-2 card">
          <h2 className="text-text-primary font-semibold mb-4">Risk Score Trend (Last 24h)</h2>
          {riskTrendData.length > 0 ? (
            <RiskTrendChart data={riskTrendData} height={220} />
          ) : (
            <div className="h-[220px] flex items-center justify-center text-text-muted text-sm">
              No trend data available
            </div>
          )}
        </div>

        {/* Alert Panel */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-text-primary font-semibold">Global Risk Alerts</h2>
            <button
              onClick={() => navigate('/alerts')}
              className="text-accent-blue text-xs hover:underline"
            >
              View all
            </button>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {alertsLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-12 bg-surface rounded-lg animate-pulse" />
              ))
            ) : alerts.length === 0 ? (
              <p className="text-text-muted text-sm text-center py-8">No active alerts</p>
            ) : (
              alerts
                .sort((a, b) => {
                  const order = { Critical: 0, Warning: 1, Informational: 2 }
                  return (order[a.severity] ?? 3) - (order[b.severity] ?? 3)
                })
                .slice(0, 8)
                .map((alert) => (
                  <div
                    key={alert.alert_id}
                    className="flex items-start gap-2 p-2.5 rounded-lg bg-surface hover:bg-border/30 transition-colors cursor-pointer"
                    onClick={() => navigate('/alerts')}
                  >
                    <SeverityBadge severity={alert.severity} size="sm" />
                    <p className="text-text-secondary text-xs line-clamp-2 flex-1">
                      {alert.message}
                    </p>
                  </div>
                ))
            )}
          </div>
        </div>
      </div>

      {/* Active Shipments Table */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-text-primary font-semibold">
            Active Shipments — Top 10 by Risk
          </h2>
          <button
            onClick={() => navigate('/shipments')}
            className="text-accent-blue text-xs hover:underline"
          >
            View all
          </button>
        </div>
        <DataTable
          columns={shipmentColumns}
          data={[...shipments].sort((a, b) => b.risk_score - a.risk_score).slice(0, 10)}
          loading={shipmentsLoading}
          onRowClick={(s) => navigate(`/shipments/${s.shipment_id}`)}
          keyExtractor={(s) => s.shipment_id}
          emptyTitle="No active shipments"
          emptyDescription="Shipments will appear here once tracking begins"
        />
      </div>

      {/* Quick Actions */}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={() => navigate('/map')}
          className="btn-secondary flex items-center gap-2"
        >
          <Map size={16} />
          View Map
        </button>
        <button
          onClick={() => navigate('/digital-twin')}
          className="btn-secondary flex items-center gap-2"
        >
          <Cpu size={16} />
          Run Simulation
        </button>
        <button
          onClick={() => navigate('/ai-chat')}
          className="btn-secondary flex items-center gap-2"
        >
          <Bot size={16} />
          AI Chat
        </button>
      </div>
    </div>
  )
}
