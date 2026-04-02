import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Search, Filter, Plus, X, CheckCircle, XCircle, Clock,
  Package, AlertTriangle, ChevronDown, Send, ClipboardList,
} from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { getShipments } from '../api/shipments'
import {
  createShipmentRequest, getShipmentRequests, reviewShipmentRequest,
  type ShipmentRequest,
} from '../api/shipmentRequests'
import { RiskBadge } from '../components/ui/RiskBadge'
import { DataTable } from '../components/ui/DataTable'
import { Pagination } from '../components/ui/Pagination'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { useAuthStore } from '../store/authStore'
import { useUIStore } from '../store/uiStore'
import type { Shipment, Column } from '../types'

const STATUS_OPTIONS = ['', 'In_Transit', 'Delayed', 'Delivered', 'Connectivity_Impaired']
const CARGO_TYPES = ['Electronics', 'Automotive Parts', 'Pharmaceuticals', 'Food & Beverage', 'Chemicals', 'Textiles', 'Machinery', 'Consumer Goods', 'Raw Materials', 'Other']
const CARRIERS = ['Maersk Line', 'DHL Express', 'FedEx Freight', 'MSC Shipping', 'UPS Supply Chain', 'COSCO Shipping', 'Evergreen Marine', 'DB Schenker']

// ─── Request Shipment Modal ───────────────────────────────────────────────────
function RequestShipmentModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)
  const [form, setForm] = useState({
    origin: '', destination: '', carrier_name: CARRIERS[0],
    cargo_type: CARGO_TYPES[0], weight_kg: 1000,
    priority: 'Normal', requested_eta: '', notes: '',
  })

  const mutation = useMutation({
    mutationFn: createShipmentRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shipment-requests'] })
      addToast({ type: 'success', title: 'Request submitted', message: 'Awaiting Manager approval' })
      onClose()
    },
    onError: () => addToast({ type: 'error', title: 'Failed to submit request' }),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.origin || !form.destination || !form.requested_eta) {
      addToast({ type: 'warning', title: 'Please fill all required fields' }); return
    }
    mutation.mutate(form)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-accent-blue/20 flex items-center justify-center">
              <Package size={18} className="text-accent-blue" />
            </div>
            <div>
              <h2 className="text-text-primary font-semibold">Request New Shipment</h2>
              <p className="text-text-muted text-xs">Requires Manager approval</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-surface text-text-muted"><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-text-secondary text-xs mb-1.5">Origin *</label>
              <input value={form.origin} onChange={e => setForm(f => ({ ...f, origin: e.target.value }))}
                placeholder="e.g. Shanghai" className="input" required />
            </div>
            <div>
              <label className="block text-text-secondary text-xs mb-1.5">Destination *</label>
              <input value={form.destination} onChange={e => setForm(f => ({ ...f, destination: e.target.value }))}
                placeholder="e.g. Rotterdam" className="input" required />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-text-secondary text-xs mb-1.5">Carrier</label>
              <select value={form.carrier_name} onChange={e => setForm(f => ({ ...f, carrier_name: e.target.value }))} className="select">
                {CARRIERS.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-text-secondary text-xs mb-1.5">Cargo Type</label>
              <select value={form.cargo_type} onChange={e => setForm(f => ({ ...f, cargo_type: e.target.value }))} className="select">
                {CARGO_TYPES.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-text-secondary text-xs mb-1.5">Weight (kg)</label>
              <input type="number" min={1} value={form.weight_kg}
                onChange={e => setForm(f => ({ ...f, weight_kg: Number(e.target.value) }))} className="input" />
            </div>
            <div>
              <label className="block text-text-secondary text-xs mb-1.5">Priority</label>
              <select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))} className="select">
                {['Normal', 'Elevated', 'High'].map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-text-secondary text-xs mb-1.5">Requested ETA *</label>
            <input type="datetime-local" value={form.requested_eta}
              onChange={e => setForm(f => ({ ...f, requested_eta: e.target.value }))}
              className="input" required />
          </div>

          <div>
            <label className="block text-text-secondary text-xs mb-1.5">Notes (optional)</label>
            <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              placeholder="Any special handling instructions..." rows={2} className="input resize-none" />
          </div>

          <div className="bg-accent-amber/10 border border-accent-amber/20 rounded-lg p-3 flex items-start gap-2">
            <AlertTriangle size={14} className="text-accent-amber shrink-0 mt-0.5" />
            <p className="text-text-secondary text-xs">This request will be sent to a Manager for approval before the shipment is created in the system.</p>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
            <button type="submit" disabled={mutation.isPending} className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50">
              {mutation.isPending ? <LoadingSpinner size="sm" /> : <Send size={15} />}
              Submit Request
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Manager Approval Panel ───────────────────────────────────────────────────
function ApprovalPanel() {
  const queryClient = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)
  const [reviewNote, setReviewNote] = useState<Record<string, string>>({})
  const [expanded, setExpanded] = useState(true)

  const { data: requests = [], isLoading } = useQuery({
    queryKey: ['shipment-requests', 'pending'],
    queryFn: () => getShipmentRequests('pending'),
    refetchInterval: 10_000,
  })

  const reviewMutation = useMutation({
    mutationFn: ({ id, action, note }: { id: string; action: 'approve' | 'reject'; note?: string }) =>
      reviewShipmentRequest(id, action, note),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['shipment-requests'] })
      queryClient.invalidateQueries({ queryKey: ['shipments'] })
      const msg = data.status === 'approved'
        ? `Shipment created: ${data.shipment_id?.slice(0, 8)}`
        : 'Request rejected'
      addToast({ type: data.status === 'approved' ? 'success' : 'info', title: `Request ${data.status}`, message: msg })
    },
    onError: () => addToast({ type: 'error', title: 'Review failed' }),
  })

  if (requests.length === 0 && !isLoading) return null

  return (
    <div className="card border-accent-amber/30 bg-accent-amber/5">
      <button className="w-full flex items-center justify-between" onClick={() => setExpanded(e => !e)}>
        <div className="flex items-center gap-2">
          <ClipboardList size={16} className="text-accent-amber" />
          <h2 className="text-text-primary font-semibold">Pending Approvals</h2>
          {requests.length > 0 && (
            <span className="bg-accent-amber text-white text-xs font-bold px-2 py-0.5 rounded-full">{requests.length}</span>
          )}
        </div>
        <ChevronDown size={16} className={`text-text-muted transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {expanded && (
        <div className="mt-4 space-y-3">
          {isLoading ? (
            <div className="flex justify-center py-4"><LoadingSpinner /></div>
          ) : (
            requests.map((req) => (
              <div key={req.request_id} className="bg-card rounded-xl border border-border p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-text-primary font-semibold text-sm">{req.origin} → {req.destination}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        req.priority === 'High' ? 'bg-accent-red/20 text-accent-red' :
                        req.priority === 'Elevated' ? 'bg-accent-amber/20 text-accent-amber' :
                        'bg-surface text-text-muted'}`}>{req.priority}</span>
                    </div>
                    <p className="text-text-secondary text-xs">
                      {req.cargo_type} · {req.weight_kg.toLocaleString()} kg · {req.carrier_name}
                    </p>
                    <p className="text-text-muted text-xs mt-0.5 flex items-center gap-1">
                      <Clock size={10} />
                      Requested ETA: {req.requested_eta ? format(new Date(req.requested_eta), 'MMM d, yyyy HH:mm') : '—'}
                    </p>
                  </div>
                  <div className="text-right shrink-0 ml-3">
                    <p className="text-text-secondary text-xs font-medium">{req.submitter_name}</p>
                    <p className="text-text-muted text-xs">{req.submitter_role}</p>
                    <p className="text-text-muted text-xs">{req.created_at ? format(parseISO(req.created_at), 'MMM d, HH:mm') : '—'}</p>
                  </div>
                </div>

                {req.notes && (
                  <p className="text-text-secondary text-xs bg-surface rounded-lg px-3 py-2 mb-3 italic">"{req.notes}"</p>
                )}

                <div className="flex gap-2 items-end">
                  <input
                    type="text"
                    value={reviewNote[req.request_id] || ''}
                    onChange={e => setReviewNote(n => ({ ...n, [req.request_id]: e.target.value }))}
                    placeholder="Optional review note..."
                    className="input text-xs flex-1 h-8"
                  />
                  <button
                    onClick={() => reviewMutation.mutate({ id: req.request_id, action: 'approve', note: reviewNote[req.request_id] })}
                    disabled={reviewMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-green/20 text-accent-green text-xs font-semibold hover:bg-accent-green/30 transition-colors disabled:opacity-50"
                  >
                    <CheckCircle size={13} /> Approve
                  </button>
                  <button
                    onClick={() => reviewMutation.mutate({ id: req.request_id, action: 'reject', note: reviewNote[req.request_id] })}
                    disabled={reviewMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-red/20 text-accent-red text-xs font-semibold hover:bg-accent-red/30 transition-colors disabled:opacity-50"
                  >
                    <XCircle size={13} /> Reject
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ─── My Requests Panel ────────────────────────────────────────────────────────
function MyRequestsPanel() {
  const { data: requests = [], isLoading } = useQuery({
    queryKey: ['shipment-requests', 'mine'],
    queryFn: () => getShipmentRequests(),
    refetchInterval: 10_000,
  })

  if (requests.length === 0 && !isLoading) return null

  const statusStyle = {
    pending: 'bg-accent-amber/20 text-accent-amber',
    approved: 'bg-accent-green/20 text-accent-green',
    rejected: 'bg-accent-red/20 text-accent-red',
  }

  return (
    <div className="card">
      <h2 className="text-text-primary font-semibold mb-3 flex items-center gap-2">
        <ClipboardList size={15} className="text-accent-blue" /> My Shipment Requests
      </h2>
      {isLoading ? <LoadingSpinner /> : (
        <div className="space-y-2">
          {requests.map(req => (
            <div key={req.request_id} className="flex items-center justify-between p-3 bg-surface rounded-lg">
              <div>
                <p className="text-text-primary text-sm font-medium">{req.origin} → {req.destination}</p>
                <p className="text-text-muted text-xs">{req.cargo_type} · {req.carrier_name}</p>
                {req.review_note && (
                  <p className="text-text-secondary text-xs mt-0.5 italic">"{req.review_note}"</p>
                )}
              </div>
              <div className="text-right shrink-0 ml-3">
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${statusStyle[req.status]}`}>
                  {req.status.charAt(0).toUpperCase() + req.status.slice(1)}
                </span>
                {req.reviewer_name && (
                  <p className="text-text-muted text-xs mt-1">by {req.reviewer_name}</p>
                )}
                {req.shipment_id && (
                  <p className="text-accent-blue text-xs font-mono mt-0.5">{req.shipment_id.slice(0, 8)}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Main Shipments Page ──────────────────────────────────────────────────────
export default function Shipments() {
  const navigate = useNavigate()
  const { role } = useAuthStore()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [riskMin, setRiskMin] = useState(0)
  const [riskMax, setRiskMax] = useState(100)
  const [showRequestModal, setShowRequestModal] = useState(false)

  const isManager = role === 'Manager' || role === 'Admin'

  const { data, isLoading } = useQuery({
    queryKey: ['shipments', { page, search, status, riskMin, riskMax }],
    queryFn: () => getShipments({ page, page_size: 20, search: search || undefined, status: status || undefined,
      risk_min: riskMin > 0 ? riskMin : undefined, risk_max: riskMax < 100 ? riskMax : undefined }),
    refetchInterval: 15_000,
  })

  const columns: Column<Shipment>[] = [
    { key: 'id', header: 'Shipment ID',
      render: (s) => <span className="font-mono text-xs text-accent-blue">{s.shipment_id.slice(0, 8)}...</span> },
    { key: 'origin', header: 'Origin',
      render: (s) => <span className="text-text-primary text-sm font-medium">{s.origin.name}</span> },
    { key: 'destination', header: 'Destination',
      render: (s) => <span className="text-text-primary text-sm">{s.destination.name}</span> },
    { key: 'carrier', header: 'Carrier',
      render: (s) => <span className="text-text-secondary text-sm">{s.carrier_name || s.carrier_id.slice(0, 8)}</span> },
    { key: 'risk', header: 'Risk Score', render: (s) => <RiskBadge score={s.risk_score} size="sm" /> },
    { key: 'eta', header: 'ETA',
      render: (s) => <span className="text-text-secondary text-sm">{s.eta ? format(parseISO(s.eta), 'MMM d, HH:mm') : '—'}</span> },
    { key: 'status', header: 'Status',
      render: (s) => (
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          s.status === 'Delayed' ? 'bg-accent-red/20 text-accent-red' :
          s.status === 'In_Transit' ? 'bg-accent-blue/20 text-accent-blue' :
          s.status === 'Connectivity_Impaired' ? 'bg-accent-amber/20 text-accent-amber' :
          'bg-accent-green/20 text-accent-green'}`}>
          {s.status.replace(/_/g, ' ')}
        </span>
      )},
    { key: 'priority', header: 'Priority',
      render: (s) => (
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          s.demand_priority === 'High' ? 'bg-accent-red/20 text-accent-red' :
          s.demand_priority === 'Elevated' ? 'bg-accent-amber/20 text-accent-amber' :
          'bg-surface text-text-muted'}`}>
          {s.demand_priority}
        </span>
      )},
    { key: 'actions', header: '',
      render: (s) => (
        <button onClick={e => { e.stopPropagation(); navigate(`/shipments/${s.shipment_id}`) }}
          className="text-accent-blue text-xs hover:underline">Details</button>
      )},
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-text-primary text-2xl font-bold">Shipments</h1>
          <p className="text-text-secondary text-sm mt-0.5">{data?.total?.toLocaleString() || '—'} total shipments</p>
        </div>
        {/* All roles can request a shipment */}
        <button onClick={() => setShowRequestModal(true)}
          className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Request Shipment
        </button>
      </div>

      {/* Manager approval queue */}
      {isManager && <ApprovalPanel />}

      {/* My requests (non-managers) */}
      {!isManager && <MyRequestsPanel />}

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-48">
            <label className="block text-text-secondary text-xs mb-1">Search</label>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input type="text" value={search} onChange={e => { setSearch(e.target.value); setPage(1) }}
                placeholder="Search by origin, destination..." className="input pl-8 h-9 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-text-secondary text-xs mb-1">Status</label>
            <select value={status} onChange={e => { setStatus(e.target.value); setPage(1) }} className="select h-9 text-sm">
              {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s || 'All Statuses'}</option>)}
            </select>
          </div>
          <div className="min-w-48">
            <label className="block text-text-secondary text-xs mb-1">
              <Filter size={12} className="inline mr-1" />Risk Range: {riskMin} – {riskMax}
            </label>
            <div className="flex items-center gap-2">
              <input type="range" min={0} max={100} value={riskMin}
                onChange={e => { setRiskMin(Number(e.target.value)); setPage(1) }} className="w-20 accent-accent-blue" />
              <span className="text-text-muted text-xs">to</span>
              <input type="range" min={0} max={100} value={riskMax}
                onChange={e => { setRiskMax(Number(e.target.value)); setPage(1) }} className="w-20 accent-accent-blue" />
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <DataTable columns={columns} data={data?.items || []} loading={isLoading}
          onRowClick={s => navigate(`/shipments/${s.shipment_id}`)}
          keyExtractor={s => s.shipment_id}
          emptyTitle="No shipments found" emptyDescription="Try adjusting your filters" />
        <Pagination page={page} total={data?.total || 0} pageSize={20} onPageChange={setPage} />
      </div>

      {showRequestModal && <RequestShipmentModal onClose={() => setShowRequestModal(false)} />}
    </div>
  )
}
