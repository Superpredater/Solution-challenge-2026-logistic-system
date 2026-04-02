import apiClient from './client'
import type { GeopoliticalRegion } from '../types'

export const getRegions = async (): Promise<GeopoliticalRegion[]> => {
  const res = await apiClient.get('/api/v1/regions')
  const data = res.data
  if (Array.isArray(data)) return data
  if (data?.items) return data.items
  return []
}

export const getRegionRisk = async (id: string): Promise<GeopoliticalRegion> => {
  const res = await apiClient.get<GeopoliticalRegion>(`/api/v1/regions/${id}/risk`)
  return res.data
}
