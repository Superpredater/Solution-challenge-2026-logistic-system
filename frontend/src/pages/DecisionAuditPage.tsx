import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, parseISO, subDays } from 'date-fns'
import { ClipboardList, ArrowRight } from 'lucide-react'
import apiClient from '../api/client'
import { DataTable } from '../components/ui/DataTable'
import { Pagination } from '../components/ui/Pagination'
import type { DecisionAuditEntry, Column } from '../types'

const LOOKBACK_OPTIONS = [
  { label: '7 days', days: 7 },
  { label: '30 days', days: 30 },
  { label: '90 days', days: 90 },
]

const DECISION_TYPE_STYLES = {
  autonomous_reroute: 'bg-accent-blue/20 text-accent-blue',
  manual_override: 'bg-accent-amber/20 text-accent-amber',
}

async function getDecisionAudit(params: {
  start: string
  end: string
  decision_type?: string
  page: number
  page_size: number
}) {
  const res = await apiClient.get('/api/v1/decisions/audit', { params })
  return res.data
}

export default function DecisionAuditPage() {
  const [lookbackDays, setLookbackDays] = useState(30)
  const [decisionType, setDecisionType] = useState('')
  const [page, setPage] = useState(1)

  const endDate = format(new Date(), 'yyyy-MM-dd')
  const startDate = format(subDays(new Date(), lookbackDays), 'yyyy-MM-dd')

  const { data, isLoading } = useQuery({
    queryKey: ['decision-audit', { startDate, endDate, decisionType, page }],
    queryFn: () =>
      getDecisionAudit({
        start: startDate,
        end: endDate,
        decision_type: decisionType || undefined,
        page,
        page_size: 25,
      }),
    refetchInterval: 30_000,
  })

  const entries: DecisionAuditEntry[] = data?.items || []

  const columns: Column<DecisionAuditEntry>[] = [
    {
      key: 'timestamp',
      header: 'Timestamp',
      render: (e) => (
        <span className="text-text-secondary text-xs whitespace-nowrap">
          {format(parseISO(e.timestamp), 'MMM d, HH:mm:ss')}
        </span>
      ),
    },
    {
      key: 'type',
      header: 'Decision Type',
      render: (e) => (
        <span
          className={`text-xs px-2.5 py-1 rounded-full font-medium ${
            DECISION_TYPE_STYLES[e.decision_type] || 'bg-surface text-text-secondary'
          }`}
        >
          {e.decision_type.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'shipment',
      header: 'Shipment',
      render: (e) => (
        <span className="text-accent-blue text-xs font-mono">{e.shipment_id.slice(0, 8)}</span>
      ),
    },
    {
      key: 'actor',
      header: 'Actor',
      render: (e) => (
        <div>
          <p className="text-text-primary text-xs font-mono">
            {e.actor === 'system' ? 'System' : e.actor.slice(0, 8)}
          </p>
          {e.actor_role && (
            <p className="text-text-muted text-xs">{e.actor_role}</p>
          )}
        </div>
      ),
    },
    {
      key: 'route',
      header: 'Route Change',
      render: (e) => (
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-text-muted font-mono">{e.previous_route_id.slice(0, 6)}</span>
          <ArrowRight size={12} className="text-text-muted" />
          <span className="text-accent-blue font-mono">{e.new_route_id.slice(0, 6)}</span>
        </div>
      ),
    },
    {
      key: 'risk',
      header: 'Trigger Risk',
      render: (e) =>
        e.triggering_risk_score != null ? (
          <span
            className={`text-xs font-semibold ${
              e.triggering_risk_score >= 70
                ? 'text-accent-red'
                : e.triggering_risk_score >= 40
                ? 'text-accent-amber'
                : 'text-accent-green'
            }`}
          >
            {e.triggering_risk_score.toFixed(1)}
          </span>
        ) : (
          <span className="text-text-muted text-xs">—</span>
        ),
    },
  ]

  const autonomousCount = entries.filter((e) => e.decision_type === 'autonomous_reroute').length
  const overrideCount = entries.filter((e) => e.decision_type === 'manual_override').length

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ClipboardList size={24} className="text-accent-blue" />
        <div>
          <h1 className="text-text-primary text-2xl font-bold">Decision Audit</h1>
          <p className="text-text-secondary text-sm mt-0.5">
            Autonomous decisions and manual overrides
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="card flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-text-secondary text-xs mb-1.5">Lookback Period</label>
          <div className="flex gap-1">
            {LOOKBACK_OPTIONS.map(({ label, days }) => (
              <button
                key={days}
                onClick={() => { setLookbackDays(days); setPage(1) }}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  lookbackDays === days
                    ? 'bg-accent-blue text-white'
                    : 'bg-surface text-text-secondary hover:text-text-primary'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-text-secondary text-xs mb-1.5">Decision Type</label>
          <select
            value={decisionType}
            onChange={(e) => { setDecisionType(e.target.value); setPage(1) }}
            className="select h-9 text-sm"
          >
            <option value="">All Types</option>
            <option value="autonomous_reroute">Autonomous Reroute</option>
            <option value="manual_override">Manual Override</option>
          </select>
        </div>
        <div className="ml-auto flex gap-4 text-sm">
          <span className="text-text-secondary">
            Autonomous: <span className="text-accent-blue font-bold">{autonomousCount}</span>
          </span>
          <span className="text-text-secondary">
            Overrides: <span className="text-accent-amber font-bold">{overrideCount}</span>
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <DataTable
          columns={columns}
          data={entries}
          loading={isLoading}
          keyExtractor={(e) => e.entry_id}
          emptyTitle="No decisions found"
          emptyDescription="No decisions recorded in the selected period"
        />
        <Pagination
          page={page}
          total={data?.total || 0}
          pageSize={25}
          onPageChange={setPage}
        />
      </div>
    </div>
  )
}
