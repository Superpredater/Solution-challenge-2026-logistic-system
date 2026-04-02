import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import { AlertTriangle, Clock, MapPin, Zap, Shield, CloudRain, Anchor, Globe } from 'lucide-react'
import apiClient from '../api/client'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const TYPE_ICONS: Record<string, React.ReactNode> = {
  weather: <CloudRain size={14} />, carrier_delay: <Clock size={14} />,
  port_closure: <Anchor size={14} />, conflict: <Shield size={14} />,
  geopolitical: <Globe size={14} />, infrastructure: <Zap size={14} />,
}
const TYPE_COLORS: Record<string, string> = {
  weather: '#3b82f6', carrier_delay: '#f59e0b', port_closure: '#8b5cf6',
  conflict: '#ef4444', geopolitical: '#f97316', infrastructure: '#64748b',
}
const SEV_STYLES: Record<string, string> = {
  Critical: 'bg-accent-red/20 text-accent-red border-accent-red/30',
  High: 'bg-accent-amber/20 text-accent-amber border-accent-amber/30',
  Medium: 'bg-accent-blue/20 text-accent-blue border-accent-blue/30',
  Low: 'bg-surface text-text-muted border-border',
}

async function getDisruptions(page = 1) {
  const res = await apiClient.get('/api/v1/disruptions', { params: { page, page_size: 25 } })
  return res.data
}

async function getDisruptionFreq() {
  const res = await apiClient.get('/api/v1/reports/disruption-frequency', {
    params: { start: '2024-01-01', end: new Date().toISOString().split('T')[0] }
  })
  return Array.isArray(res.data) ? res.data : res.data?.items || []
}

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1e2235', border: '1px solid #2a2d3e', borderRadius: 8 },
  labelStyle: { color: '#94a3b8' }, itemStyle: { color: '#f1f5f9' },
}

export default function DisruptionsPage() {
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState('All')

  const { data, isLoading } = useQuery({
    queryKey: ['disruptions', page],
    queryFn: () => getDisruptions(page),
    refetchInterval: 30_000,
  })

  const { data: freqData = [] } = useQuery({
    queryKey: ['disruption-freq'],
    queryFn: getDisruptionFreq,
  })

  const items = data?.items || []
  const filtered = filter === 'All' ? items : items.filter((d: any) => d.severity === filter)

  const criticalCount = items.filter((d: any) => d.severity === 'Critical').length
  const activeCount = items.filter((d: any) => !d.resolved_at).length

  const chartData = freqData.map((d: any) => ({
    type: d.disruption_type?.replace('_', ' ') || d.type,
    count: d.disruption_count || d.count || 0,
    fill: TYPE_COLORS[d.disruption_type] || '#64748b',
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-accent-amber/20 flex items-center justify-center">
          <AlertTriangle size={20} className="text-accent-amber" />
        </div>
        <div>
          <h1 className="text-text-primary text-2xl font-bold">Disruptions</h1>
          <p className="text-text-secondary text-sm mt-0.5">Active transit disruptions and incident tracking</p>
        </div>
        {criticalCount > 0 && (
          <div className="ml-auto flex items-center gap-2 text-xs text-accent-red bg-accent-red/10 border border-accent-red/20 px-3 py-1.5 rounded-full animate-pulse">
            <AlertTriangle size={12} />
            {criticalCount} Critical Active
          </div>
        )}
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Active Disruptions', value: activeCount, color: 'text-accent-red' },
          { label: 'Critical Severity', value: criticalCount, color: 'text-accent-red' },
          { label: 'High Severity', value: items.filter((d: any) => d.severity === 'High').length, color: 'text-accent-amber' },
          { label: 'Total This Period', value: items.length, color: 'text-text-primary' },
        ].map(({ label, value, color }) => (
          <div key={label} className="card text-center">
            <p className={`text-3xl font-bold ${color}`}>{isLoading ? '—' : value}</p>
            <p className="text-text-secondary text-xs mt-1">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Frequency chart */}
        <div className="xl:col-span-2 card">
          <h2 className="text-text-primary font-semibold mb-4">Disruption Frequency by Type</h2>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                <XAxis dataKey="type" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} angle={-20} textAnchor="end" />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip {...TOOLTIP_STYLE} />
                <Bar dataKey="count" name="Incidents" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry: any, i: number) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-56 flex items-center justify-center"><LoadingSpinner /></div>
          )}
        </div>

        {/* Type legend */}
        <div className="card">
          <h2 className="text-text-primary font-semibold mb-4">Disruption Types</h2>
          <div className="space-y-3">
            {Object.entries(TYPE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                  <span className="text-text-secondary text-sm capitalize flex items-center gap-1.5">
                    {TYPE_ICONS[type]} {type.replace('_', ' ')}
                  </span>
                </div>
                <span className="text-text-muted text-xs">
                  {chartData.find((d: any) => d.type === type.replace('_', ' '))?.count || 0}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filter + table */}
      <div className="card p-0 overflow-hidden">
        <div className="flex items-center gap-2 p-4 border-b border-border flex-wrap">
          <h2 className="text-text-primary font-semibold mr-2">Active Disruptions</h2>
          {['All', 'Critical', 'High', 'Medium', 'Low'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                filter === f ? 'bg-accent-blue text-white' : 'bg-surface text-text-secondary hover:text-text-primary'
              }`}>{f}</button>
          ))}
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12"><LoadingSpinner /></div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <AlertTriangle size={32} className="text-text-muted mx-auto mb-3" />
            <p className="text-text-secondary font-medium">No disruptions found</p>
            <p className="text-text-muted text-sm mt-1">All clear for the selected filter</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filtered.map((d: any) => (
              <div key={d.disruption_id} className="flex items-start gap-4 p-4 hover:bg-surface/50 transition-colors">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  style={{ backgroundColor: (TYPE_COLORS[d.disruption_type] || '#64748b') + '22', color: TYPE_COLORS[d.disruption_type] || '#64748b' }}>
                  {TYPE_ICONS[d.disruption_type] || <AlertTriangle size={14} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${SEV_STYLES[d.severity] || SEV_STYLES.Low}`}>
                      {d.severity}
                    </span>
                    <span className="text-text-muted text-xs capitalize">{d.disruption_type?.replace('_', ' ')}</span>
                  </div>
                  <p className="text-text-primary text-sm font-medium">{d.description}</p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-text-muted">
                    <span className="flex items-center gap-1"><Clock size={11} />
                      {d.started_at ? format(parseISO(d.started_at), 'MMM d, HH:mm') : '—'}
                    </span>
                    {d.affected_node_ids?.length > 0 && (
                      <span className="flex items-center gap-1"><MapPin size={11} />
                        {d.affected_node_ids.length} node{d.affected_node_ids.length > 1 ? 's' : ''} affected
                      </span>
                    )}
                    <span className="text-accent-blue">{d.source}</span>
                  </div>
                </div>
                {!d.resolved_at && (
                  <div className="flex items-center gap-1.5 text-xs text-accent-red shrink-0">
                    <div className="w-1.5 h-1.5 rounded-full bg-accent-red animate-pulse" />
                    Active
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Cell imported above
