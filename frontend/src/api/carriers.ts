import apiClient from './client'
import type { CarrierProfile } from '../types'

export const getCarriers = async (): Promise<CarrierProfile[]> => {
  const res = await apiClient.get('/api/v1/carriers')
  // Backend returns either a plain array or { items: [...] }
  const data = res.data
  if (Array.isArray(data)) return data
  if (data?.items) return data.items
  return []
}

export const getCarrierProfile = async (id: string): Promise<CarrierProfile> => {
  const res = await apiClient.get<CarrierProfile>(`/api/v1/carriers/${id}/profile`)
  return res.data
}

export const getCarrierRiskHistory = async (id: string): Promise<{ risk_score: number; recorded_at: string }[]> => {
  const res = await apiClient.get(`/api/v1/carriers/${id}/risk-history`)
  const data = res.data
  if (Array.isArray(data)) return data
  if (data?.items) return data.items
  return []
}
