import apiClient from './client'
import type { DigitalTwinScenario, ScenarioParameters } from '../types'

export const createScenario = async (data: {
  scenario_name: string
  parameters: ScenarioParameters
}): Promise<{ scenario_id: string; status: string; estimated_completion_seconds: number }> => {
  const res = await apiClient.post('/api/v1/digital-twin/scenarios', data)
  return res.data
}

export const getScenario = async (id: string): Promise<DigitalTwinScenario> => {
  const res = await apiClient.get<DigitalTwinScenario>(`/api/v1/digital-twin/scenarios/${id}`)
  return res.data
}

export const getScenarioReport = async (id: string) => {
  const res = await apiClient.get(`/api/v1/digital-twin/scenarios/${id}/report`)
  return res.data
}

export const getScenarios = async (): Promise<DigitalTwinScenario[]> => {
  const res = await apiClient.get<DigitalTwinScenario[]>('/api/v1/digital-twin/scenarios')
  return res.data
}
