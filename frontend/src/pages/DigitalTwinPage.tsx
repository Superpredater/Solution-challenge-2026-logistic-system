import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import {
  GitBranch, Play, Clock, CheckCircle, XCircle, Plus, Trash2,
  Package, Route, Cpu, Truck, CloudRain, Shield, Anchor, AlertTriangle,
  TrendingUp, BarChart2, ChevronDown, ChevronUp, Info,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadialBarChart, RadialBar, Cell,
} from 'recharts'
import { createScenario, getScenario, getScenarios } from '../api/digitalTwin'
import { getCarriers } from '../api/carriers'
import { getShipments } from '../api/shipments'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { useUIStore } from '../store/uiStore'
import type { DigitalTwinScenario } from '../types'

// ─── Preset scenarios ─────────────────────────────────────────────────────────
const PRESETS = [
  { name: 'Suez Canal Closure', icon: Anchor, color: '#ef4444',
    desc: 'Simulates full closure of the Suez Canal, forcing rerouting via Cape of Good Hope',
    params: { node_closures: ['suez-canal-node'], conflict_zone_activations: [], carrier_capacity_reductions: [], weather_events: [] } },
  { name: 'Red Sea Conflict Escalation', icon: Shield, color: '#f97316',
    desc: 'War-zone activation across Red Sea corridor affecting all transit routes',
    params: { node_closures: [], conflict_zone_activations: ['red-sea-region'], carrier_capacity_reductions: [], weather_events: [] } },
  { name: 'Trans-Pacific Storm', icon: CloudRain, color: '#3b82f6',
    desc: 'Category 5 typhoon injecting high weather risk across Pacific shipping lanes',
    params: { node_closures: [], conflict_zone_activations: [], carrier_capacity_reductions: [], weather_events: [{ region_id: 'pacific-region', risk_delta: 45 }] } },
  { name: 'Major Carrier Collapse', icon: Truck, color: '#f59e0b',
    desc: 'Simulates 80% capacity reduction across top 3 carriers simultaneously',
    params: { node_closures: [], conflict_zone_activations: [], carrier_capacity_reductions: [{ carrier_id: 'carrier-0001', reduction_pct: 80 }, { carrier_id: 'carrier-0002', reduction_pct: 80 }], weather_events: [] } },
]

// ─── Status badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: DigitalTwinScenario['status'] }) {
  const cfg = {
    running: { cls: 'bg-accent-blue/20 text-accent-blue', icon: <LoadingSpinner size="sm" /> },
    completed: { cls: 'bg-accent-green/20 text-accent-green', icon: <CheckCircle size={12} /> },
    failed: { cls: 'bg-accent-red/20 text-accent-red', icon: <XCircle size={12} /> },
  }[status] ?? { cls: 'bg-surface text-text-muted', icon: null }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.icon}{status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

// ─── Countdown timer ──────────────────────────────────────────────────────────
function Countdown({ seconds, onDone }: { seconds: number; onDone: () => void }) {
  const [left, setLeft] = useState(seconds)
  useEffect(() => {
    if (left <= 0) { onDone(); return }
    const t = setTimeout(() => setLeft(l => l - 1), 1000)
    return () => clearTimeout(t)
  }, [left])
  const pct = Math.round(((seconds - left) / seconds) * 100)
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-text-secondary">
        <span>Computing impact on up to 10,000 shipments…</span>
        <span className="font-mono text-accent-blue">{left}s remaining</span>
      </div>
      <div className="h-2 bg-surface rounded-full overflow-hidden">
        <div className="h-full bg-accent-blue rounded-full transition-all duration-1000" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

// ─── Network Snapshot panel ───────────────────────────────────────────────────
function NetworkSnapshot() {
  const { data: shipmentsData } = useQuery({
    queryKey: ['shipments', { page: 1, page_size: 10 }],
    queryFn: () => getShipments({ page: 1, page_size: 10 }),
  })
  const { data: carriers = [] } = useQuery({ queryKey: ['carriers'], queryFn: getCarriers })

  const total = shipmentsData?.total || 0
  const capacity = Math.min(100, Math.round((total / 10000) * 100))

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Cpu size={16} className="text-accent-blue" />
        <h2 className="text-text-primary font-semibold">Network Snapshot</h2>
        <span className="ml-auto text-xs text-accent-green bg-accent-green/10 px-2 py-0.5 rounded-full">Live</span>
      </div>
      <div className="grid grid-cols-2 gap-3 mb-4">
        {[
          { icon: Package, label: 'Active Shipments', value: total.toLocaleString(), sub: `/ 10,000 capacity`, color: 'text-accent-blue' },
          { icon: Route, label: 'Transit Nodes', value: '247', sub: 'Ports, hubs, warehouses', color: 'text-accent-amber' },
          { icon: Truck, label: 'Carriers Tracked', value: carriers.length, sub: 'Rolling 90-day data', color: 'text-accent-green' },
          { icon: BarChart2, label: 'Routes Modelled', value: total > 0 ? total : '—', sub: 'Active route legs', color: 'text-text-primary' },
        ].map(({ icon: Icon, label, value, sub, color }) => (
          <div key={label} className="bg-surface rounded-lg p-3">
            <Icon size={14} className={`${color} mb-1.5`} />
            <p className={`text-lg font-bold ${color}`}>{value}</p>
            <p className="text-text-secondary text-xs">{label}</p>
            <p className="text-text-muted text-xs">{sub}</p>
          </div>
        ))}
      </div>
      {/* Capacity bar */}
      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-text-muted">Simulation capacity used</span>
          <span className="text-text-secondary font-medium">{capacity}% of 10,000</span>
        </div>
        <div className="h-2 bg-surface rounded-full overflow-hidden">
          <div className="h-full rounded-full transition-all"
            style={{ width: `${capacity}%`, backgroundColor: capacity > 80 ? '#ef4444' : capacity > 50 ? '#f59e0b' : '#22c55e' }} />
        </div>
      </div>
    </div>
  )
}

// ─── Simulation Report ────────────────────────────────────────────────────────
function SimulationReport({ scenario }: { scenario: DigitalTwinScenario }) {
  const [expanded, setExpanded] = useState(true)
  const r = scenario.result
  if (!r) return null

  const impactData = [
    { name: 'Affected', value: r.affected_shipment_count, fill: '#ef4444' },
    { name: 'Unaffected', value: Math.max(0, 40 - r.affected_shipment_count), fill: '#22c55e' },
  ]
  const etaData = [
    { range: '0–4h', count: Math.round(r.affected_shipment_count * 0.3) },
    { range: '4–12h', count: Math.round(r.affected_shipment_count * 0.35) },
    { range: '12–24h', count: Math.round(r.affected_shipment_count * 0.2) },
    { range: '24h+', count: Math.round(r.affected_shipment_count * 0.15) },
  ]

  return (
    <div className="card border-accent-green/30 bg-accent-green/5">
      <button className="w-full flex items-center justify-between mb-4" onClick={() => setExpanded(e => !e)}>
        <div className="flex items-center gap-2">
          <CheckCircle size={16} className="text-accent-green" />
          <h2 className="text-text-primary font-semibold">Simulation Report</h2>
          <span className="text-text-muted text-xs">— {scenario.scenario_name}</span>
        </div>
        {expanded ? <ChevronUp size={16} className="text-text-muted" /> : <ChevronDown size={16} className="text-text-muted" />}
      </button>

      {expanded && (
        <div className="space-y-5">
          {/* KPI row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-card rounded-xl p-4 text-center border border-border">
              <p className="text-text-muted text-xs mb-1">Affected Shipments</p>
              <p className="text-accent-red text-3xl font-bold">{r.affected_shipment_count}</p>
              <p className="text-text-muted text-xs mt-1">out of ~40 active</p>
            </div>
            <div className="bg-card rounded-xl p-4 text-center border border-border">
              <p className="text-text-muted text-xs mb-1">Avg ETA Deviation</p>
              <p className="text-accent-amber text-3xl font-bold">{r.average_eta_deviation_hours.toFixed(1)}h</p>
              <p className="text-text-muted text-xs mt-1">average delay</p>
            </div>
            <div className="bg-card rounded-xl p-4 text-center border border-border">
              <p className="text-text-muted text-xs mb-1">Mitigations</p>
              <p className="text-accent-blue text-3xl font-bold">{r.mitigation_recommendations.length}</p>
              <p className="text-text-muted text-xs mt-1">actions available</p>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-text-secondary text-xs font-semibold mb-2">Impact Distribution</p>
              <ResponsiveContainer width="100%" height={140}>
                <RadialBarChart innerRadius="40%" outerRadius="80%" data={impactData} startAngle={180} endAngle={0}>
                  <RadialBar dataKey="value" cornerRadius={4}>
                    {impactData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </RadialBar>
                  <Tooltip contentStyle={{ background: '#1e2235', border: '1px solid #2a2d3e', borderRadius: 8 }} />
                </RadialBarChart>
              </ResponsiveContainer>
              <div className="flex justify-center gap-4 text-xs">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-accent-red inline-block" /> Affected</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-accent-green inline-block" /> Unaffected</span>
              </div>
            </div>
            <div>
              <p className="text-text-secondary text-xs font-semibold mb-2">ETA Deviation Breakdown</p>
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={etaData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                  <XAxis dataKey="range" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#1e2235', border: '1px solid #2a2d3e', borderRadius: 8 }} />
                  <Bar dataKey="count" fill="#f59e0b" radius={[3, 3, 0, 0]} name="Shipments" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Mitigation recommendations */}
          <div>
            <p className="text-text-secondary text-xs font-semibold mb-2 flex items-center gap-1.5">
              <TrendingUp size={12} className="text-accent-blue" /> Recommended Mitigation Actions
            </p>
            <div className="space-y-2">
              {r.mitigation_recommendations.map((rec, i) => (
                <div key={i} className="flex items-start gap-3 bg-card rounded-lg p-3 border border-border">
                  <span className="w-5 h-5 rounded-full bg-accent-blue/20 text-accent-blue text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                  <p className="text-text-secondary text-sm leading-relaxed">{rec}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function DigitalTwinPage() {
  const queryClient = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)

  // Form state
  const [scenarioName, setScenarioName] = useState('')
  const [nodeClosures, setNodeClosures] = useState<string[]>([])
  const [conflictZones, setConflictZones] = useState<string[]>([])
  const [capacityReductions, setCapacityReductions] = useState<{ carrier_id: string; reduction_pct: number }[]>([])
  const [weatherEvents, setWeatherEvents] = useState<{ region_id: string; risk_delta: number }[]>([])
  const [newNodeId, setNewNodeId] = useState('')
  const [newZoneId, setNewZoneId] = useState('')
  const [newWeatherRegion, setNewWeatherRegion] = useState('')
  const [newWeatherDelta, setNewWeatherDelta] = useState(20)
  const [runningId, setRunningId] = useState<string | null>(null)
  const [showCountdown, setShowCountdown] = useState(false)
  const [countdownSecs, setCountdownSecs] = useState(60)

  const { data: scenarios = [], isLoading: scenariosLoading } = useQuery({
    queryKey: ['scenarios'],
    queryFn: getScenarios,
    refetchInterval: 8_000,
  })

  const { data: carriers = [] } = useQuery({ queryKey: ['carriers'], queryFn: getCarriers })

  const { data: runningScenario } = useQuery({
    queryKey: ['scenario', runningId],
    queryFn: () => getScenario(runningId!),
    enabled: !!runningId,
    refetchInterval: 2_000,
  })

  useEffect(() => {
    if (!runningScenario) return
    if (runningScenario.status === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] })
      addToast({ type: 'success', title: 'Simulation complete', message: runningScenario.scenario_name })
      setRunningId(null); setShowCountdown(false)
    } else if (runningScenario.status === 'failed') {
      addToast({ type: 'error', title: 'Simulation failed' })
      setRunningId(null); setShowCountdown(false)
    }
  }, [runningScenario?.status])

  const createMutation = useMutation({
    mutationFn: createScenario,
    onSuccess: (data) => {
      setRunningId(data.scenario_id)
      setShowCountdown(true)
      setCountdownSecs(data.estimated_completion_seconds || 60)
      queryClient.invalidateQueries({ queryKey: ['scenarios'] })
      addToast({ type: 'info', title: 'Simulation started', message: `Computing impact on up to 10,000 shipments` })
      resetForm()
    },
    onError: () => addToast({ type: 'error', title: 'Failed to start simulation' }),
  })

  const resetForm = () => {
    setScenarioName(''); setNodeClosures([]); setConflictZones([])
    setCapacityReductions([]); setWeatherEvents([])
  }

  const applyPreset = (preset: typeof PRESETS[0]) => {
    setScenarioName(preset.name)
    setNodeClosures(preset.params.node_closures)
    setConflictZones(preset.params.conflict_zone_activations)
    setCapacityReductions(preset.params.carrier_capacity_reductions as any)
    setWeatherEvents(preset.params.weather_events as any)
  }

  const handleRun = () => {
    if (!scenarioName.trim()) { addToast({ type: 'warning', title: 'Scenario name required' }); return }
    createMutation.mutate({
      scenario_name: scenarioName,
      parameters: { node_closures: nodeClosures, conflict_zone_activations: conflictZones, carrier_capacity_reductions: capacityReductions, weather_events: weatherEvents },
    })
  }

  const latestCompleted = (scenarios as DigitalTwinScenario[]).find(s => s.status === 'completed' && s.result)
  const isRunning = createMutation.isPending || !!runningId

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-accent-blue/20 flex items-center justify-center">
          <GitBranch size={20} className="text-accent-blue" />
        </div>
        <div>
          <h1 className="text-text-primary text-2xl font-bold">Digital Twin Simulation</h1>
          <p className="text-text-secondary text-sm mt-0.5">Model disruption scenarios against your live supply chain network</p>
        </div>
        <div className="ml-auto flex items-center gap-1.5 text-xs text-text-muted bg-surface border border-border px-3 py-1.5 rounded-full">
          <Info size={12} />
          Supports up to 10,000 concurrent shipments
        </div>
      </div>

      {/* Network snapshot */}
      <NetworkSnapshot />

      {/* Running simulation progress */}
      {showCountdown && runningScenario?.status === 'running' && (
        <div className="card border-accent-blue/30 bg-accent-blue/5">
          <div className="flex items-center gap-2 mb-3">
            <LoadingSpinner size="sm" />
            <span className="text-accent-blue font-semibold text-sm">Simulation Running — {runningScenario.scenario_name}</span>
          </div>
          <Countdown seconds={countdownSecs} onDone={() => setShowCountdown(false)} />
          <p className="text-text-muted text-xs mt-2">
            Computing projected ETA deviations and Risk_Score changes for all affected shipments…
          </p>
        </div>
      )}

      {/* Latest result */}
      {latestCompleted && <SimulationReport scenario={latestCompleted} />}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Scenario Builder */}
        <div className="card space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-text-primary font-semibold">Scenario Builder</h2>
            <button onClick={resetForm} className="text-text-muted text-xs hover:text-text-primary">Clear</button>
          </div>

          {/* Preset quick-launch */}
          <div>
            <p className="text-text-secondary text-xs mb-2 font-medium">Quick Presets</p>
            <div className="grid grid-cols-2 gap-2">
              {PRESETS.map(p => (
                <button key={p.name} onClick={() => applyPreset(p)}
                  className="text-left p-2.5 rounded-lg border border-border bg-surface hover:border-accent-blue/40 transition-colors group">
                  <div className="flex items-center gap-2 mb-1">
                    <p.icon size={13} style={{ color: p.color }} />
                    <span className="text-text-primary text-xs font-medium leading-tight">{p.name}</span>
                  </div>
                  <p className="text-text-muted text-xs leading-snug line-clamp-2">{p.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-border" />

          {/* Name */}
          <div>
            <label className="block text-text-secondary text-xs mb-1.5">Scenario Name *</label>
            <input type="text" value={scenarioName} onChange={e => setScenarioName(e.target.value)}
              placeholder="e.g. Suez Canal Closure" className="input" />
          </div>

          {/* 1. Node Closures (Transit_Node closure) */}
          <div>
            <label className="block text-text-secondary text-xs mb-1.5 flex items-center gap-1.5">
              <Anchor size={12} className="text-accent-amber" /> Transit Node Closures
            </label>
            <div className="space-y-1.5">
              {nodeClosures.map((id, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="flex-1 bg-surface rounded-lg px-3 py-1.5 font-mono text-xs text-text-primary">{id}</span>
                  <button onClick={() => setNodeClosures(nodeClosures.filter((_, j) => j !== i))} className="text-text-muted hover:text-accent-red"><Trash2 size={13} /></button>
                </div>
              ))}
              <div className="flex gap-2">
                <input type="text" value={newNodeId} onChange={e => setNewNodeId(e.target.value)}
                  placeholder="Node ID or name (e.g. suez-canal)" className="input text-xs flex-1"
                  onKeyDown={e => { if (e.key === 'Enter' && newNodeId.trim()) { setNodeClosures([...nodeClosures, newNodeId.trim()]); setNewNodeId('') } }} />
                <button onClick={() => { if (newNodeId.trim()) { setNodeClosures([...nodeClosures, newNodeId.trim()]); setNewNodeId('') } }} className="btn-secondary px-3"><Plus size={13} /></button>
              </div>
            </div>
          </div>

          {/* 2. Conflict Zones (geographic conflict zone activation) */}
          <div>
            <label className="block text-text-secondary text-xs mb-1.5 flex items-center gap-1.5">
              <Shield size={12} className="text-accent-red" /> Conflict Zone Activations
            </label>
            <div className="space-y-1.5">
              {conflictZones.map((id, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="flex-1 bg-surface rounded-lg px-3 py-1.5 font-mono text-xs text-text-primary">{id}</span>
                  <button onClick={() => setConflictZones(conflictZones.filter((_, j) => j !== i))} className="text-text-muted hover:text-accent-red"><Trash2 size={13} /></button>
                </div>
              ))}
              <div className="flex gap-2">
                <input type="text" value={newZoneId} onChange={e => setNewZoneId(e.target.value)}
                  placeholder="Region ID (e.g. red-sea-region)" className="input text-xs flex-1"
                  onKeyDown={e => { if (e.key === 'Enter' && newZoneId.trim()) { setConflictZones([...conflictZones, newZoneId.trim()]); setNewZoneId('') } }} />
                <button onClick={() => { if (newZoneId.trim()) { setConflictZones([...conflictZones, newZoneId.trim()]); setNewZoneId('') } }} className="btn-secondary px-3"><Plus size={13} /></button>
              </div>
            </div>
          </div>

          {/* 3. Carrier Capacity Reductions */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-text-secondary text-xs flex items-center gap-1.5">
                <Truck size={12} className="text-accent-amber" /> Carrier Capacity Reductions
              </label>
              <button onClick={() => carriers.length > 0 && setCapacityReductions([...capacityReductions, { carrier_id: carriers[0].carrier_id, reduction_pct: 30 }])}
                className="text-accent-blue text-xs hover:underline flex items-center gap-1"><Plus size={11} />Add</button>
            </div>
            <div className="space-y-2">
              {capacityReductions.map((cr, i) => (
                <div key={i} className="flex items-center gap-2">
                  <select value={cr.carrier_id} onChange={e => { const u = [...capacityReductions]; u[i] = { ...u[i], carrier_id: e.target.value }; setCapacityReductions(u) }}
                    className="select flex-1 text-xs h-8">
                    {carriers.map(c => <option key={c.carrier_id} value={c.carrier_id}>{c.name}</option>)}
                  </select>
                  <input type="number" min={0} max={100} value={cr.reduction_pct}
                    onChange={e => { const u = [...capacityReductions]; u[i] = { ...u[i], reduction_pct: Number(e.target.value) }; setCapacityReductions(u) }}
                    className="input w-16 text-xs h-8" />
                  <span className="text-text-muted text-xs">%</span>
                  <button onClick={() => setCapacityReductions(capacityReductions.filter((_, j) => j !== i))} className="text-text-muted hover:text-accent-red"><Trash2 size={13} /></button>
                </div>
              ))}
            </div>
          </div>

          {/* 4. Weather Events */}
          <div>
            <label className="block text-text-secondary text-xs mb-1.5 flex items-center gap-1.5">
              <CloudRain size={12} className="text-accent-blue" /> Weather Event Injection
            </label>
            <div className="space-y-1.5">
              {weatherEvents.map((w, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="flex-1 bg-surface rounded-lg px-3 py-1.5 text-xs text-text-primary">{w.region_id} <span className="text-accent-amber">+{w.risk_delta} risk</span></span>
                  <button onClick={() => setWeatherEvents(weatherEvents.filter((_, j) => j !== i))} className="text-text-muted hover:text-accent-red"><Trash2 size={13} /></button>
                </div>
              ))}
              <div className="flex gap-2">
                <input type="text" value={newWeatherRegion} onChange={e => setNewWeatherRegion(e.target.value)}
                  placeholder="Region ID" className="input text-xs flex-1" />
                <input type="number" min={1} max={100} value={newWeatherDelta} onChange={e => setNewWeatherDelta(Number(e.target.value))}
                  className="input w-16 text-xs" placeholder="Δ risk" />
                <button onClick={() => { if (newWeatherRegion.trim()) { setWeatherEvents([...weatherEvents, { region_id: newWeatherRegion.trim(), risk_delta: newWeatherDelta }]); setNewWeatherRegion('') } }}
                  className="btn-secondary px-3"><Plus size={13} /></button>
              </div>
            </div>
          </div>

          <button onClick={handleRun} disabled={isRunning}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-sm font-semibold disabled:opacity-50">
            {isRunning ? <><LoadingSpinner size="sm" />Running Simulation…</> : <><Play size={16} />Run Simulation</>}
          </button>
        </div>

        {/* History */}
        <div className="card">
          <h2 className="text-text-primary font-semibold mb-4">Scenario History</h2>
          {scenariosLoading ? (
            <div className="flex justify-center py-8"><LoadingSpinner /></div>
          ) : (scenarios as DigitalTwinScenario[]).length === 0 ? (
            <div className="text-center py-12">
              <GitBranch size={32} className="text-text-muted mx-auto mb-3 opacity-40" />
              <p className="text-text-secondary font-medium">No scenarios run yet</p>
              <p className="text-text-muted text-sm mt-1">Use the builder or a preset to start</p>
            </div>
          ) : (
            <div className="space-y-2">
              {(scenarios as DigitalTwinScenario[]).map(s => (
                <div key={s.scenario_id} className="p-3 bg-surface rounded-xl border border-border hover:border-border/60 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-text-primary text-sm font-medium">{s.scenario_name}</p>
                    <StatusBadge status={s.status} />
                  </div>
                  {s.result && (
                    <div className="flex gap-4 text-xs mb-2">
                      <span className="text-accent-red font-medium">{s.result.affected_shipment_count} affected</span>
                      <span className="text-accent-amber font-medium">+{s.result.average_eta_deviation_hours.toFixed(1)}h avg delay</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1 text-text-muted text-xs">
                    <Clock size={10} />
                    {s.created_at ? format(parseISO(s.created_at), 'MMM d, HH:mm') : '—'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
