import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, parseISO } from 'date-fns'
import { Bell, X, Package } from 'lucide-react'
import { getAlerts, getAlertDeliveries } from '../api/alerts'
import { SeverityBadge } from '../components/ui/SeverityBadge'
import { DataTable } from '../components/ui/DataTable'
import { Pagination } from '../components/ui/Pagination'
import { useUIStore } from '../store/uiStore'
import type { Alert, AlertDelivery, Column } from '../types'

type SeverityFilter = 'All' | 'Critical' | 'Warning' | 'Informational'

const TABS: SeverityFilter[] = ['All', 'Critical', 'Warning', 'Informational']

function AlertDetailModal({
  alert,
  onClose,
}: {
  alert: Alert
  onClose: () => void
}) {
  const { data: deliveries } = useQuery({
    queryKey: ['alert-deliveries', alert.alert_id],
    queryFn: () => getAlertDeliveries(alert.alert_id),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-card border border-border rounded-2xl w-full max-w-2xl shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <Bell size={20} className="text-accent-amber" />
            <div>
              <h2 className="text-text-primary font-semibold">Alert Details</h2>
              <p className="text-text-muted text-xs font-mono">{alert.alert_id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface transition-colors text-text-muted"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-5">
          <div className="flex items-center gap-3 flex-wrap">
            <SeverityBadge severity={alert.severity} />
            <span className="text-xs px-2.5 py-1 rounded-full bg-surface text-text-secondary">
              {alert.trigger_type.replace(/_/g, ' ')}
            </span>
          </div>

          <div>
            <p className="text-text-secondary text-xs uppercase tracking-wide mb-1">Message</p>
            <p className="text-text-primary text-sm leading-relaxed">{alert.message}</p>
          </div>

          {alert.ai_explanation && (
            <div className="bg-surface rounded-lg p-4">
              <p className="text-text-secondary text-xs uppercase tracking-wide mb-2">AI Explanation</p>
              <p className="text-text-primary text-sm leading-relaxed">{alert.ai_explanation}</p>
            </div>
          )}

          {alert.shipment_id && (
            <div className="flex items-center gap-2 text-sm">
              <Package size={14} className="text-text-muted" />
              <span className="text-text-secondary">Shipment:</span>
              <span className="text-accent-blue font-mono text-xs">{alert.shipment_id}</span>
            </div>
          )}

          <div>
            <p className="text-text-secondary text-xs uppercase tracking-wide mb-1">Created</p>
            <p className="text-text-primary text-sm">
              {format(parseISO(alert.created_at), 'MMM d, yyyy HH:mm:ss')}
            </p>
          </div>

          {/* Delivery Audit */}
          <div>
            <p className="text-text-secondary text-xs uppercase tracking-wide mb-3">Delivery Audit</p>
            {deliveries && deliveries.length > 0 ? (
              <div className="space-y-2">
                {(deliveries as AlertDelivery[]).map((d) => (
                  <div
                    key={d.delivery_id}
                    className="flex items-center justify-between bg-surface rounded-lg px-3 py-2 text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-text-secondary capitalize">{d.channel}</span>
                      <span className="text-text-muted text-xs">·</span>
                      <span className="text-text-muted text-xs font-mono">
                        {d.stakeholder_id.slice(0, 8)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          d.status === 'delivered'
                            ? 'bg-accent-green/20 text-accent-green'
                            : d.status === 'failed'
                            ? 'bg-accent-red/20 text-accent-red'
                            : 'bg-surface text-text-muted'
                        }`}
                      >
                        {d.status}
                      </span>
                      {d.retry_count > 0 && (
                        <span className="text-text-muted text-xs">{d.retry_count} retries</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-text-muted text-sm">No delivery records</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AlertsPage() {
  const [activeTab, setActiveTab] = useState<SeverityFilter>('All')
  const [page, setPage] = useState(1)
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const setUnreadAlertCount = useUIStore((s) => s.setUnreadAlertCount)

  const { data, isLoading } = useQuery({
    queryKey: ['alerts', { severity: activeTab === 'All' ? undefined : activeTab, page }],
    queryFn: () =>
      getAlerts({
        severity: activeTab === 'All' ? undefined : activeTab,
        page,
        page_size: 25,
      }),
    refetchInterval: 15_000,
  })

  // Clear unread count when viewing alerts
  useEffect(() => {
    setUnreadAlertCount(0)
  }, [data])

  const columns: Column<Alert>[] = [
    {
      key: 'severity',
      header: 'Severity',
      render: (a) => <SeverityBadge severity={a.severity} size="sm" />,
    },
    {
      key: 'trigger',
      header: 'Trigger',
      render: (a) => (
        <span className="text-text-secondary text-xs px-2 py-0.5 rounded bg-surface">
          {a.trigger_type.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'message',
      header: 'Message',
      render: (a) => (
        <span className="text-text-primary text-sm line-clamp-1">{a.message}</span>
      ),
    },
    {
      key: 'shipment',
      header: 'Shipment',
      render: (a) =>
        a.shipment_id ? (
          <span className="text-accent-blue text-xs font-mono">{a.shipment_id.slice(0, 8)}</span>
        ) : (
          <span className="text-text-muted text-xs">—</span>
        ),
    },
    {
      key: 'time',
      header: 'Created',
      render: (a) => (
        <span className="text-text-muted text-xs whitespace-nowrap">
          {format(parseISO(a.created_at), 'MMM d, HH:mm')}
        </span>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-text-primary text-2xl font-bold">Alerts</h1>
        <p className="text-text-secondary text-sm mt-0.5">
          {data?.total?.toLocaleString() || '—'} total alerts
        </p>
      </div>

      {/* Severity Tabs */}
      <div className="flex gap-1 bg-surface rounded-xl p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); setPage(1) }}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-card text-text-primary shadow-sm'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <DataTable
          columns={columns}
          data={data?.items || []}
          loading={isLoading}
          onRowClick={setSelectedAlert}
          keyExtractor={(a) => a.alert_id}
          emptyTitle="No alerts"
          emptyDescription="No alerts match the current filter"
        />
        <Pagination
          page={page}
          total={data?.total || 0}
          pageSize={25}
          onPageChange={setPage}
        />
      </div>

      {selectedAlert && (
        <AlertDetailModal alert={selectedAlert} onClose={() => setSelectedAlert(null)} />
      )}
    </div>
  )
}
