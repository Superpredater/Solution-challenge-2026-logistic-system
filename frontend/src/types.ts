// Core domain types matching backend Pydantic models

export type Role = 'Viewer' | 'Analyst' | 'Manager' | 'Admin'
export type WarState = 'Safe' | 'Caution' | 'High_Risk' | 'Restricted'
export type TransportMode = 'air' | 'sea' | 'rail' | 'road'
export type ShipmentStatus = 'In_Transit' | 'Delayed' | 'Delivered' | 'Connectivity_Impaired'
export type DemandPriority = 'Normal' | 'Elevated' | 'High'
export type AlertSeverity = 'Informational' | 'Warning' | 'Critical'
export type DisruptionSeverity = 'Low' | 'Medium' | 'High' | 'Critical'
export type DecisionType = 'autonomous_reroute' | 'manual_override'
export type RecommendationStatus = 'pending' | 'accepted' | 'rejected' | 'auto_applied'

export interface Shipment {
  shipment_id: string
  tenant_id: string
  origin: TransitNodeRef
  destination: TransitNodeRef
  active_route_id: string
  carrier_id: string
  carrier_name?: string
  status: ShipmentStatus
  risk_score: number
  risk_score_updated_at: string
  eta: string
  eta_confidence_interval: [string, string]
  demand_priority: DemandPriority
  carbon_kg: number
  edge_agent_id?: string
  created_at: string
  updated_at: string
}

export interface TransitNodeRef {
  node_id: string
  name: string
  latitude?: number
  longitude?: number
}

export interface RouteLeg {
  leg_id: string
  sequence: number
  origin_node_id: string
  origin_name?: string
  destination_node_id: string
  destination_name?: string
  transport_mode: TransportMode
  carrier_id: string
  estimated_duration_hours: number
  estimated_cost_usd: number
  carbon_kg: number
}

export interface Route {
  route_id: string
  tenant_id: string
  shipment_id: string
  legs: RouteLeg[]
  total_distance_km: number
  total_estimated_duration_hours: number
  total_estimated_cost_usd: number
  total_carbon_kg: number
  is_active: boolean
  created_at: string
}

export interface RerouteRecommendation {
  recommendation_id: string
  shipment_id: string
  tenant_id: string
  triggering_risk_score: number
  disruption_id: string
  candidate_route: Route
  new_eta: string
  cost_delta_usd: number
  carbon_delta_kg: number
  rank_score: number
  status: RecommendationStatus
  created_at: string
  decided_at?: string
  decided_by?: string
}

export interface Alert {
  alert_id: string
  tenant_id: string
  shipment_id?: string
  disruption_id?: string
  severity: AlertSeverity
  trigger_type: string
  message: string
  ai_explanation?: string
  created_at: string
  deliveries: AlertDelivery[]
}

export interface AlertDelivery {
  delivery_id: string
  alert_id: string
  stakeholder_id: string
  channel: 'email' | 'sms' | 'webhook'
  status: 'delivered' | 'failed' | 'suppressed'
  delivered_at?: string
  retry_count: number
}

export interface Disruption {
  disruption_id: string
  disruption_type: string
  affected_region_id?: string
  affected_node_ids: string[]
  severity: DisruptionSeverity
  description: string
  source: string
  started_at: string
  resolved_at?: string
  created_at: string
}

export interface GeopoliticalRegion {
  region_id: string
  name: string
  iso_codes: string[]
  geopolitical_risk_index: number
  war_state: WarState
  risk_index_updated_at: string
  war_state_updated_at: string
  geometry?: Record<string, unknown>
}

export interface CarrierProfile {
  carrier_id: string
  name: string
  on_time_rate_90d: number
  on_time_rate_30d: number
  incident_count_90d: number
  capacity_reliability_score: number
  risk_score: number
  is_high_risk: boolean
  profile_updated_at: string
}

export interface RiskScoreEvent {
  event_id: string
  shipment_id: string
  tenant_id: string
  risk_score: number
  weather_component: number
  operational_component: number
  war_state_component: number
  geopolitical_component: number
  recorded_at: string
}

export interface DecisionAuditEntry {
  entry_id: string
  tenant_id: string
  shipment_id: string
  decision_type: DecisionType
  triggering_risk_score?: number
  recommendation_id?: string
  actor: string
  actor_role?: string
  previous_route_id: string
  new_route_id: string
  timestamp: string
}

export interface AIInteractionLog {
  interaction_id: string
  tenant_id: string
  stakeholder_id: string
  interaction_type: string
  query: string
  response: string
  model_used: string
  latency_ms: number
  fallback_used: boolean
  timestamp: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  latency_ms?: number
  fallback_used?: boolean
}

export interface DigitalTwinScenario {
  scenario_id: string
  scenario_name: string
  status: 'running' | 'completed' | 'failed'
  parameters: ScenarioParameters
  result?: ScenarioResult
  created_at: string
  completed_at?: string
}

export interface ScenarioParameters {
  node_closures: string[]
  conflict_zone_activations: string[]
  carrier_capacity_reductions: { carrier_id: string; reduction_pct: number }[]
  weather_events: { region_id: string; risk_delta: number }[]
}

export interface ScenarioResult {
  affected_shipment_count: number
  average_eta_deviation_hours: number
  mitigation_recommendations: string[]
}

export interface CarbonSummary {
  tenant_id: string
  total_carbon_kg: number
  shipment_count: number
  period_start: string
  period_end: string
  by_mode: { mode: TransportMode; carbon_kg: number }[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface User {
  stakeholder_id: string
  tenant_id: string
  email: string
  name?: string
  role: Role
  phone?: string
  company?: string
  job_title?: string
  bio?: string
  location?: string
  avatar?: string          // base64 data URL
  webhook_url?: string
  notification_channels: ('email' | 'sms' | 'webhook')[]
  created_at?: string
}

// Re-export Column type for convenience
export type { Column } from './components/ui/DataTable'
