import apiClient from './client'
import type { Disruption } from '../types'

export const getDisruptions = async (): Promise<Disruption[]> => {
  const res = await apiClient.get<Disruption[]>('/api/v1/disruptions')
  return res.data
}
