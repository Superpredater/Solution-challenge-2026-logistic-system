import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, subDays } from 'date-fns'
import { Download, BarChart2, TrendingUp, AlertTriangle, Leaf } from 'lucide-react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import {
  getCarrierPerformanceReport,
  getDisruptionFrequencyReport,
  getRiskScoreTrendReport,
  exportReport,
} from '../api/reports'
import { getCarbonSummary } from '../api/carbon'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { useUIStore } from '../store/uiStore'

type ReportTab = 'risk-trend' | 'carrier-performance' | 'disruption-frequency' | 'co2'

const TABS = [
  { id: 'risk-trend' as ReportTab, label: 'Risk Score Trend', icon: TrendingUp },
  { id: 'carrier-performance' as ReportTab, label: 'Carrier Performance', icon: BarChart2 },
  { id: 'disruption-frequency' as ReportTab, label: 'Disruption Frequency', icon: AlertTriangle },
  { id: 'co2' as ReportTab, label: 'CO₂ Emissions', icon: Leaf },
]

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1e2235', border: '1px solid #2a2d3e', borderRadius: 8 },
  labelStyle: { color: '#94a3b8' },
  itemStyle: { color: '#f1f5f9' },
}

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState<ReportTab>('risk-trend')
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const addToast = useUIStore((s) => s.addToast)

  const params = { start: startDate, end: endDate }

  const { data: riskTrend, isLoading: riskLoading } = useQuery({
    queryKey: ['report-risk-trend', params],
    queryFn: () => getRiskScoreTrendReport(params),
    enabled: activeTab === 'risk-trend',
  })

  const { data: carrierPerf, isLoading: carrierLoading } = useQuery({
    queryKey: ['report-carrier-perf', params],
    queryFn: () => getCarrierPerformanceReport(params),
    enabled: activeTab === 'carrier-performance',
  })

  const { data: disruptions, isLoading: disruptionLoading } = useQuery({
    queryKey: ['report-disruptions', params],
    queryFn: () => getDisruptionFrequencyReport(params),
    enabled: activeTab === 'disruption-frequency',
  })

  const { data: carbon, isLoading: carbonLoading } = useQuery({
    queryKey: ['carbon-summary', params],
    queryFn: () => getCarbonSummary({ start: startDate, end: endDate }),
    enabled: activeTab === 'co2',
  })

  const handleExport = async (fmt: 'csv' | 'json') => {
    try {
      const reportType =
        activeTab === 'risk-trend'
          ? 'risk-score-trend'
          : activeTab === 'carrier-performance'
          ? 'carrier-performance'
          : 'disruption-frequency'

      const blob = await exportReport(reportType as 'carrier-performance' | 'disruption-frequency' | 'risk-score-trend', params, fmt)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${reportType}-${startDate}-${endDate}.${fmt}`
      a.click()
      URL.revokeObjectURL(url)
      addToast({ type: 'success', title: 'Export started', message: `Downloading ${fmt.toUpperCase()} report` })
    } catch {
      addToast({ type: 'error', title: 'Export failed' })
    }
  }

  const isLoading = riskLoading || carrierLoading || disruptionLoading || carbonLoading

  // Normalize data for charts
  const riskChartData = Array.isArray(riskTrend) ? riskTrend : []
  const carrierChartData = Array.isArray(carrierPerf) ? carrierPerf : []
  const disruptionChartData = Array.isArray(disruptions) ? disruptions : []

  const carbonByMode = carbon?.by_mode || []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-text-primary text-2xl font-bold">Reports</h1>
        <p className="text-text-secondary text-sm mt-0.5">Analytics and performance reports</p>
      </div>

      {/* Date range + export */}
      <div className="card flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-text-secondary text-xs mb-1">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="input h-9 text-sm w-40"
          />
        </div>
        <div>
          <label className="block text-text-secondary text-xs mb-1">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="input h-9 text-sm w-40"
          />
        </div>
        <div className="ml-auto flex gap-2">
          {activeTab !== 'co2' && (
            <>
              <button
                onClick={() => handleExport('csv')}
                className="btn-secondary flex items-center gap-2 text-xs py-2"
              >
                <Download size={14} />
                CSV
              </button>
              <button
                onClick={() => handleExport('json')}
                className="btn-secondary flex items-center gap-2 text-xs py-2"
              >
                <Download size={14} />
                JSON
              </button>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-surface rounded-xl p-1 w-fit flex-wrap">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              activeTab === id
                ? 'bg-card text-text-primary shadow-sm'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Chart area */}
      <div className="card">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <>
            {activeTab === 'risk-trend' && (
              <div>
                <h2 className="text-text-primary font-semibold mb-4">Risk Score Trend</h2>
                {riskChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={320}>
                    <LineChart data={riskChartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                      <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip {...TOOLTIP_STYLE} />
                      <Line type="monotone" dataKey="avg_risk_score" stroke="#3b82f6" strokeWidth={2} dot={false} name="Avg Risk" />
                      <Line type="monotone" dataKey="max_risk_score" stroke="#ef4444" strokeWidth={1.5} dot={false} strokeDasharray="4 4" name="Max Risk" />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-64 flex items-center justify-center text-text-muted text-sm">
                    No data for selected period
                  </div>
                )}
              </div>
            )}

            {activeTab === 'carrier-performance' && (
              <div>
                <h2 className="text-text-primary font-semibold mb-4">Carrier On-Time Performance</h2>
                {carrierChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={carrierChartData} margin={{ top: 5, right: 10, left: -20, bottom: 40 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                      <XAxis dataKey="carrier_name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} angle={-30} textAnchor="end" />
                      <YAxis domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
                      <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
                      <Bar dataKey="on_time_rate_90d" fill="#3b82f6" name="90d Rate" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="on_time_rate_30d" fill="#22c55e" name="30d Rate" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-64 flex items-center justify-center text-text-muted text-sm">
                    No data for selected period
                  </div>
                )}
              </div>
            )}

            {activeTab === 'disruption-frequency' && (
              <div>
                <h2 className="text-text-primary font-semibold mb-4">Disruption Frequency by Type</h2>
                {disruptionChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={disruptionChartData} margin={{ top: 5, right: 10, left: -20, bottom: 40 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                      <XAxis dataKey="disruption_type" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} angle={-30} textAnchor="end" />
                      <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip {...TOOLTIP_STYLE} />
                      <Bar dataKey="count" fill="#f59e0b" name="Count" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-64 flex items-center justify-center text-text-muted text-sm">
                    No data for selected period
                  </div>
                )}
              </div>
            )}

            {activeTab === 'co2' && (
              <div>
                <h2 className="text-text-primary font-semibold mb-4">CO₂ Emissions Summary</h2>
                {carbon ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <div className="bg-surface rounded-xl p-4 text-center">
                        <p className="text-text-muted text-xs mb-1">Total CO₂</p>
                        <p className="text-text-primary text-2xl font-bold">
                          {(carbon.total_carbon_kg / 1000).toFixed(1)}t
                        </p>
                      </div>
                      <div className="bg-surface rounded-xl p-4 text-center">
                        <p className="text-text-muted text-xs mb-1">Shipments</p>
                        <p className="text-text-primary text-2xl font-bold">{carbon.shipment_count}</p>
                      </div>
                      <div className="bg-surface rounded-xl p-4 text-center">
                        <p className="text-text-muted text-xs mb-1">Avg per Shipment</p>
                        <p className="text-text-primary text-2xl font-bold">
                          {carbon.shipment_count > 0
                            ? (carbon.total_carbon_kg / carbon.shipment_count).toFixed(0)
                            : 0}
                          kg
                        </p>
                      </div>
                    </div>
                    {carbonByMode.length > 0 && (
                      <ResponsiveContainer width="100%" height={240}>
                        <AreaChart data={carbonByMode} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                          <XAxis dataKey="mode" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                          <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                          <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => `${v.toFixed(0)} kg`} />
                          <Area type="monotone" dataKey="carbon_kg" stroke="#22c55e" fill="#22c55e" fillOpacity={0.2} name="CO₂ (kg)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                ) : (
                  <div className="h-64 flex items-center justify-center text-text-muted text-sm">
                    No data for selected period
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
