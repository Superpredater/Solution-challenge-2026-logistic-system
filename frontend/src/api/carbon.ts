import apiClient from './client'
import type { CarbonSummary } from '../types'

export const getCarbonSummary = async (params: {
  start?: string
  end?: string
}): Promise<CarbonSummary> => {
  const res = await apiClient.get<CarbonSummary>('/api/v1/carbon/summary', { params })
  return res.data
}
