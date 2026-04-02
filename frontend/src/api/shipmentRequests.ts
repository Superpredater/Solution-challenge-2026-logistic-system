import apiClient from './client'

export interface ShipmentRequest {
  request_id: string
  submitted_by: string
  submitter_name: string
  submitter_role: string
  origin: string
  destination: string
  carrier_name: string
  cargo_type: string
  weight_kg: number
  priority: string
  requested_eta: string
  notes?: string
  status: 'pending' | 'approved' | 'rejected'
  reviewed_by?: string
  reviewer_name?: string
  review_note?: string
  reviewed_at?: string
  shipment_id?: string
  created_at: string
}

export interface CreateShipmentRequest {
  origin: string
  destination: string
  carrier_name: string
  cargo_type: string
  weight_kg: number
  priority: string
  requested_eta: string
  notes?: string
}

export const createShipmentRequest = async (data: CreateShipmentRequest): Promise<ShipmentRequest> => {
  const res = await apiClient.post('/api/v1/shipment-requests', data)
  return res.data
}

export const getShipmentRequests = async (status?: string): Promise<ShipmentRequest[]> => {
  const res = await apiClient.get('/api/v1/shipment-requests', { params: status ? { status } : {} })
  return Array.isArray(res.data) ? res.data : []
}

export const reviewShipmentRequest = async (
  requestId: string,
  action: 'approve' | 'reject',
  review_note?: string
): Promise<ShipmentRequest> => {
  const res = await apiClient.patch(`/api/v1/shipment-requests/${requestId}/review`, { action, review_note })
  return res.data
}

export const getPendingCount = async (): Promise<number> => {
  const res = await apiClient.get('/api/v1/shipment-requests/pending-count')
  return res.data.count || 0
}
