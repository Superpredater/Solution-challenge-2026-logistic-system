import apiClient from './client'

export interface ReportParams {
  start: string
  end: string
  format?: 'json' | 'csv'
}

export const getCarrierPerformanceReport = async (params: ReportParams) => {
  const res = await apiClient.get('/api/v1/reports/carrier-performance', { params })
  return res.data
}

export const getDisruptionFrequencyReport = async (params: ReportParams) => {
  const res = await apiClient.get('/api/v1/reports/disruption-frequency', { params })
  return res.data
}

export const getRiskScoreTrendReport = async (params: ReportParams) => {
  const res = await apiClient.get('/api/v1/reports/risk-score-trend', { params })
  return res.data
}

export const exportReport = async (
  type: 'carrier-performance' | 'disruption-frequency' | 'risk-score-trend',
  params: ReportParams,
  format: 'csv' | 'json'
): Promise<Blob> => {
  const res = await apiClient.get(`/api/v1/reports/${type}`, {
    params: { ...params, format },
    responseType: 'blob',
  })
  return res.data
}
