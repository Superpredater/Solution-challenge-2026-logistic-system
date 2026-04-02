import apiClient from './client'
import type { Alert, PaginatedResponse } from '../types'

export interface AlertFilters {
  severity?: string
  page?: number
  page_size?: number
}

export const getAlerts = async (filters: AlertFilters = {}): Promise<PaginatedResponse<Alert>> => {
  const res = await apiClient.get('/api/v1/alerts', { params: filters })
  return res.data
}

export const getAlert = async (id: string): Promise<Alert> => {
  const res = await apiClient.get<Alert>(`/api/v1/alerts/${id}`)
  return res.data
}

export const getAlertDeliveries = async (id: string) => {
  const res = await apiClient.get(`/api/v1/alerts/${id}/deliveries`)
  return res.data
}
