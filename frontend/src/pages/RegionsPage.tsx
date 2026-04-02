import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import { Globe, Shield, AlertTriangle, TrendingUp, MapPin, Clock } from 'lucide-react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from 'recharts'
import { getRegions } from '../api/regions'
import { WarStateBadge } from '../components/ui/WarStateBadge'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import type { GeopoliticalRegion } from '../types'

const WAR_STATE_ORDER = { Restricted: 0, High_Risk: 1, Caution: 2, Safe: 3 }
const WAR_STATE_COLORS: Record<string, string> = {
  Restricted: '#ef4444', High_Risk: '#f97316', Caution: '#eab308', Safe: '#22c55e',
}
const WAR_STATE_BG: Record<string, string> = {
  Restricted: 'bg-accent-red/10 border-accent-red/20',
  High_Risk: 'bg-orange-500/10 border-orange-500/20',
  Caution: 'bg-accent-amber/10 border-accent-amber/20',
  Safe: 'bg-accent-green/10 border-accent-green/20',
}

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1e2235', border: '1px solid #2a2d3e', borderRadius: 8 },
  labelStyle: { color: '#94a3b8' }, itemStyle: { color: '#f1f5f9' },
}

export default function RegionsPage() {
  const [selected, setSelected] = useState<GeopoliticalRegion | null>(null)
  const [filter, setFilter] = useState<string>('All')

  const { data: regions = [], isLoading } = useQuery({
    queryKey: ['regions'],
    queryFn: getRegions,
    refetchInterval: 60_000,
  })

  const sorted = [...regions].sort((a, b) =>
    (WAR_STATE_ORDER[a.war_state] ?? 4) - (WAR_STATE_ORDER[b.war_state] ?? 4)
  )
  const filtered = filter === 'All' ? sorted : sorted.filter(r => r.war_state === filter)

  const restricted = regions.filter(r => r.war_state === 'Restricted').length
  const highRisk = regions.filter(r => r.war_state === 'High_Risk').length
  const caution = regions.filter(r => r.war_state === 'Caution').length
  const safe = regions.filter(r => r.war_state === 'Safe').length
  const avgGeoRisk = regions.length
    ? (regions.reduce((s, r) => s + r.geopolitical_risk_index, 0) / regions.length).toFixed(1)
    : '0'

  const barData = sorted.map(r => ({
    name: r.name.length > 14 ? r.name.slice(0, 14) + '…' : r.name,
    risk: r.geopolitical_risk_index,
    fill: WAR_STATE_COLORS[r.war_state] || '#64748b',
  }))

  const radarData = selected ? [
    { subject: 'Geo Risk', value: selected.geopolitical_risk_index },
    { subject: 'Conflict', value: selected.war_state === 'Restricted' ? 100 : selected.war_state === 'High_Risk' ? 75 : selected.war_state === 'Caution' ? 40 : 5 },
    { subject: 'Trade Risk', value: Math.round(selected.geopolitical_risk_index * 0.8) },
    { subject: 'Stability', value: 100 - selected.geopolitical_risk_index },
    { subject: 'Sanctions', value: Math.round(selected.geopolitical_risk_index * 0.6) },
  ] : []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-accent-blue/20 flex items-center justify-center">
          <Globe size={20} className="text-accent-blue" />
        </div>
        <div>
          <h1 className="text-text-primary text-2xl font-bold">Geopolitical Regions</h1>
          <p className="text-text-secondary text-sm mt-0.5">War-state monitoring and geopolitical risk intelligence</p>
        </div>
        {restricted > 0 && (
          <div className="ml-auto flex items-center gap-2 text-xs text-accent-red bg-accent-red/10 border border-accent-red/20 px-3 py-1.5 rounded-full">
            <Shield size={12} />
            {restricted} Restricted Zone{restricted > 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Restricted', value: restricted, color: 'text-accent-red', bg: 'bg-accent-red/10' },
          { label: 'High Risk', value: highRisk, color: 'text-orange-400', bg: 'bg-orange-500/10' },
          { label: 'Caution', value: caution, color: 'text-accent-amber', bg: 'bg-accent-amber/10' },
          { label: 'Safe', value: safe, color: 'text-accent-green', bg: 'bg-accent-green/10' },
          { label: 'Avg Geo Risk', value: avgGeoRisk, color: 'text-accent-blue', bg: 'bg-accent-blue/10' },
        ].map(({ label, value, color, bg }) => (
          <div key={label} className="card text-center">
            <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center mx-auto mb-2`}>
              <Globe size={16} className={color} />
            </div>
            <p className={`text-2xl font-bold ${color}`}>{isLoading ? '—' : value}</p>
            <p className="text-text-muted text-xs mt-1">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Risk index bar chart */}
        <div className="xl:col-span-2 card">
          <h2 className="text-text-primary font-semibold mb-4">Geopolitical Risk Index by Region</h2>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={barData} margin={{ top: 5, right: 10, left: -10, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} angle={-30} textAnchor="end" />
                <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [v.toFixed(1), 'Risk Index']} />
                <Bar dataKey="risk" radius={[4, 4, 0, 0]}>
                  {barData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-60 flex items-center justify-center"><LoadingSpinner /></div>
          )}
        </div>

        {/* Selected region radar */}
        <div className="card">
          <h2 className="text-text-primary font-semibold mb-3">
            {selected ? selected.name : 'Select a Region'}
          </h2>
          {selected && radarData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#2a2d3e" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10 }} />
                  <Radar dataKey="value" stroke={WAR_STATE_COLORS[selected.war_state]} fill={WAR_STATE_COLORS[selected.war_state]} fillOpacity={0.3} />
                </RadarChart>
              </ResponsiveContainer>
              <div className="space-y-2 mt-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-text-muted">War State</span>
                  <WarStateBadge warState={selected.war_state} size="sm" />
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Geo Risk Index</span>
                  <span className="text-text-primary font-bold">{selected.geopolitical_risk_index.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Last Updated</span>
                  <span className="text-text-secondary">
                    {selected.risk_index_updated_at ? format(parseISO(selected.risk_index_updated_at), 'MMM d, HH:mm') : '—'}
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="h-48 flex flex-col items-center justify-center text-text-muted gap-2">
              <Globe size={32} className="opacity-30" />
              <p className="text-sm">Click a region card to see details</p>
            </div>
          )}
        </div>
      </div>

      {/* Region cards */}
      <div>
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <h2 className="text-text-primary font-semibold mr-2">All Regions</h2>
          {['All', 'Restricted', 'High_Risk', 'Caution', 'Safe'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                filter === f ? 'bg-accent-blue text-white' : 'bg-surface text-text-secondary hover:text-text-primary'
              }`}>{f.replace('_', ' ')}</button>
          ))}
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12"><LoadingSpinner /></div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {filtered.map(region => (
              <button
                key={region.region_id}
                onClick={() => setSelected(region)}
                className={`text-left p-4 rounded-xl border transition-all hover:shadow-lg ${
                  selected?.region_id === region.region_id
                    ? 'border-accent-blue bg-accent-blue/10'
                    : `${WAR_STATE_BG[region.war_state] || 'bg-surface border-border'} hover:border-opacity-60`
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <MapPin size={14} className="text-text-muted shrink-0 mt-0.5" />
                    <p className="text-text-primary font-semibold text-sm">{region.name}</p>
                  </div>
                  <WarStateBadge warState={region.war_state} size="sm" />
                </div>

                {/* Risk index bar */}
                <div className="mb-2">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-text-muted">Geo Risk Index</span>
                    <span className="font-bold" style={{ color: WAR_STATE_COLORS[region.war_state] }}>
                      {region.geopolitical_risk_index.toFixed(1)}
                    </span>
                  </div>
                  <div className="h-1.5 bg-surface rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${region.geopolitical_risk_index}%`,
                        backgroundColor: WAR_STATE_COLORS[region.war_state],
                      }}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-1 text-text-muted text-xs">
                  <Clock size={10} />
                  Updated {region.risk_index_updated_at ? format(parseISO(region.risk_index_updated_at), 'MMM d, HH:mm') : '—'}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
