import apiClient from './client'
import type { Shipment, RerouteRecommendation, RiskScoreEvent, PaginatedResponse, Route } from '../types'

export interface ShipmentFilters {
  status?: string
  risk_min?: number
  risk_max?: number
  search?: string
  page?: number
  page_size?: number
}

export const getShipments = async (filters: ShipmentFilters = {}): Promise<PaginatedResponse<Shipment>> => {
  const res = await apiClient.get('/api/v1/shipments', { params: filters })
  return res.data
}

export const getShipment = async (id: string): Promise<Shipment> => {
  const res = await apiClient.get<Shipment>(`/api/v1/shipments/${id}`)
  return res.data
}

export const getShipmentRoute = async (id: string): Promise<Route> => {
  const res = await apiClient.get<Route>(`/api/v1/shipments/${id}/route`)
  return res.data
}

export const getShipmentRecommendations = async (id: string): Promise<RerouteRecommendation[]> => {
  const res = await apiClient.get<RerouteRecommendation[]>(`/api/v1/shipments/${id}/recommendations`)
  return res.data
}

export const acceptRecommendation = async (
  shipmentId: string,
  recId: string,
  notes?: string
): Promise<{ shipment_id: string; new_route_id: string; new_eta: string; status: string }> => {
  const res = await apiClient.post(`/api/v1/shipments/${shipmentId}/recommendations/${recId}/accept`, { notes })
  return res.data
}

export const rejectRecommendation = async (
  shipmentId: string,
  recId: string,
  reason?: string
): Promise<void> => {
  await apiClient.post(`/api/v1/shipments/${shipmentId}/recommendations/${recId}/reject`, { reason })
}

export const getShipmentRiskHistory = async (id: string, hours = 48): Promise<RiskScoreEvent[]> => {
  const res = await apiClient.get<RiskScoreEvent[]>(`/api/v1/shipments/${id}/risk-history`, {
    params: { hours },
  })
  return res.data
}

export const getShipmentAIExplanation = async (id: string): Promise<{
  explanation: string
  generated_at: string
  fallback_used: boolean
}> => {
  const res = await apiClient.get(`/api/v1/shipments/${id}/ai-explanation`)
  return res.data
}

export const getShipmentCarbon = async (id: string): Promise<{ carbon_kg: number; by_leg: { leg_id: string; carbon_kg: number }[] }> => {
  const res = await apiClient.get(`/api/v1/shipments/${id}/carbon`)
  return res.data
}
