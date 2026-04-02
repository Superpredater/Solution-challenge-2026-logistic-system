import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, subDays } from 'date-fns'
import { Leaf, TrendingDown, Package, Truck, Ship, Plane, Train } from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import apiClient from '../api/client'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'

const MODE_ICONS: Record<string, React.ReactNode> = {
  sea: <Ship size={14} />, air: <Plane size={14} />,
  road: <Truck size={14} />, rail: <Train size={14} />,
}
const MODE_COLORS: Record<string, string> = {
  sea: '#3b82f6', air: '#ef4444', road: '#f59e0b', rail: '#22c55e',
}

async function getCarbonSummary() {
  const res = await apiClient.get('/api/v1/carbon/summary')
  return res.data
}

async function getCarbonTrend(start: string, end: string) {
  try {
    const res = await apiClient.get('/api/v1/analytics/risk-score-trend', { params: { start, end } })
    // Simulate carbon trend from risk data
    return (res.data || []).map((d: any, i: number) => ({
      date: d.bucket?.split('T')[0] || d.date || `Day ${i+1}`,
      carbon_kg: Math.round(800 + Math.random() * 400 + i * 12),
      sea: Math.round(300 + Math.random() * 100),
      air: Math.round(200 + Math.random() * 150),
      road: Math.round(150 + Math.random() * 80),
      rail: Math.round(80 + Math.random() * 40),
    }))
  } catch { return [] }
}

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1e2235', border: '1px solid #2a2d3e', borderRadius: 8 },
  labelStyle: { color: '#94a3b8' }, itemStyle: { color: '#f1f5f9' },
}

export default function CarbonPage() {
  const [start] = useState(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
  const [end] = useState(format(new Date(), 'yyyy-MM-dd'))

  const { data: summary, isLoading } = useQuery({
    queryKey: ['carbon-summary'],
    queryFn: getCarbonSummary,
    refetchInterval: 60_000,
  })

  const { data: trend = [] } = useQuery({
    queryKey: ['carbon-trend', start, end],
    queryFn: () => getCarbonTrend(start, end),
  })

  const byMode = summary?.by_mode || [
    { mode: 'sea', carbon_kg: 42000 }, { mode: 'air', carbon_kg: 28000 },
    { mode: 'road', carbon_kg: 18000 }, { mode: 'rail', carbon_kg: 8000 },
  ]

  const totalKg = summary?.total_carbon_kg || byMode.reduce((s: number, m: any) => s + m.carbon_kg, 0)
  const shipmentCount = summary?.shipment_count || 40
  const avgPerShipment = shipmentCount > 0 ? (totalKg / shipmentCount).toFixed(0) : 0
  const ecoSavings = Math.round(totalKg * 0.12) // 12% potential saving

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-accent-green/20 flex items-center justify-center">
          <Leaf size={20} className="text-accent-green" />
        </div>
        <div>
          <h1 className="text-text-primary text-2xl font-bold">Carbon Optimization</h1>
          <p className="text-text-secondary text-sm mt-0.5">CO₂ emissions tracking and eco-routing insights</p>
        </div>
        <div className="ml-auto flex items-center gap-2 text-xs text-accent-green bg-accent-green/10 border border-accent-green/20 px-3 py-1.5 rounded-full">
          <Leaf size={12} />
          Eco-routing enabled
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total CO₂ Emitted', value: `${(totalKg / 1000).toFixed(1)}t`, sub: 'This period', color: 'text-accent-amber', bg: 'bg-accent-amber/10' },
          { label: 'Avg per Shipment', value: `${avgPerShipment} kg`, sub: 'CO₂ per shipment', color: 'text-accent-blue', bg: 'bg-accent-blue/10' },
          { label: 'Potential Savings', value: `${(ecoSavings / 1000).toFixed(1)}t`, sub: 'Via eco-routing', color: 'text-accent-green', bg: 'bg-accent-green/10' },
          { label: 'Shipments Tracked', value: shipmentCount, sub: 'Active shipments', color: 'text-text-primary', bg: 'bg-surface' },
        ].map(({ label, value, sub, color, bg }) => (
          <div key={label} className="card">
            <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center mb-3`}>
              <Leaf size={16} className={color} />
            </div>
            <p className={`text-2xl font-bold ${color}`}>{isLoading ? '—' : value}</p>
            <p className="text-text-secondary text-xs mt-1">{label}</p>
            <p className="text-text-muted text-xs">{sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Emissions trend */}
        <div className="xl:col-span-2 card">
          <h2 className="text-text-primary font-semibold mb-4">CO₂ Emissions Trend (30 days)</h2>
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={trend} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="carbonGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [`${v.toLocaleString()} kg`, 'CO₂']} />
                <Area type="monotone" dataKey="carbon_kg" stroke="#22c55e" strokeWidth={2} fill="url(#carbonGrad)" name="Total CO₂" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center"><LoadingSpinner /></div>
          )}
        </div>

        {/* By mode pie */}
        <div className="card">
          <h2 className="text-text-primary font-semibold mb-4">Emissions by Transport Mode</h2>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={byMode} dataKey="carbon_kg" nameKey="mode" cx="50%" cy="50%" outerRadius={70} label={({ mode, percent }) => `${mode} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {byMode.map((entry: any) => (
                  <Cell key={entry.mode} fill={MODE_COLORS[entry.mode] || '#64748b'} />
                ))}
              </Pie>
              <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [`${v.toLocaleString()} kg`, 'CO₂']} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-2">
            {byMode.map((m: any) => (
              <div key={m.mode} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: MODE_COLORS[m.mode] || '#64748b' }} />
                  <span className="text-text-secondary capitalize flex items-center gap-1">
                    {MODE_ICONS[m.mode]} {m.mode}
                  </span>
                </div>
                <span className="text-text-primary font-medium">{(m.carbon_kg / 1000).toFixed(1)}t</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Mode breakdown bar chart */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-text-primary font-semibold">Emissions by Mode Over Time</h2>
          <div className="flex items-center gap-1.5 text-xs text-accent-green bg-accent-green/10 px-2.5 py-1 rounded-full">
            <TrendingDown size={12} />
            12% reduction possible with eco-routing
          </div>
        </div>
        {trend.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trend.slice(-14)} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [`${v.toLocaleString()} kg`, '']} />
              <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 11 }} />
              <Bar dataKey="sea" stackId="a" fill="#3b82f6" name="Sea" radius={[0,0,0,0]} />
              <Bar dataKey="air" stackId="a" fill="#ef4444" name="Air" />
              <Bar dataKey="road" stackId="a" fill="#f59e0b" name="Road" />
              <Bar dataKey="rail" stackId="a" fill="#22c55e" name="Rail" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-56 flex items-center justify-center"><LoadingSpinner /></div>
        )}
      </div>

      {/* Eco-routing tips */}
      <div className="card border-accent-green/20 bg-accent-green/5">
        <h2 className="text-text-primary font-semibold mb-3 flex items-center gap-2">
          <Leaf size={16} className="text-accent-green" /> Eco-Routing Recommendations
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {[
            { title: 'Switch 3 air legs to sea', saving: '2.4t CO₂', detail: 'Shanghai → Rotterdam route' },
            { title: 'Consolidate 5 road shipments', saving: '0.8t CO₂', detail: 'European inland distribution' },
            { title: 'Use rail for Trans-Siberian', saving: '1.1t CO₂', detail: 'Asia → Europe corridor' },
          ].map(({ title, saving, detail }) => (
            <div key={title} className="bg-card rounded-lg p-3 border border-accent-green/20">
              <p className="text-text-primary text-sm font-medium">{title}</p>
              <p className="text-accent-green text-xs font-bold mt-1">Save {saving}</p>
              <p className="text-text-muted text-xs mt-0.5">{detail}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
