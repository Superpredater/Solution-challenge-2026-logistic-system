"""Pydantic v2 models for the Smart Supply Chain Optimization platform."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Risk configuration
# ---------------------------------------------------------------------------

class RiskWeights(BaseModel):
    w_weather: float = Field(default=0.25, ge=0.0, le=1.0)
    w_operational: float = Field(default=0.30, ge=0.0, le=1.0)
    w_war: float = Field(default=0.25, ge=0.0, le=1.0)
    w_geopolitical: float = Field(default=0.20, ge=0.0, le=1.0)


class RiskThreshold(BaseModel):
    name: str
    threshold: float = Field(ge=0.0, le=100.0)
    action: str


# ---------------------------------------------------------------------------
# Tenant & Stakeholder
# ---------------------------------------------------------------------------

class Tenant(BaseModel):
    tenant_id: UUID
    name: str
    mfa_enabled: bool = False
    eco_routing_enabled: bool = False
    autonomous_decision_enabled: bool = False
    risk_score_weights: RiskWeights = Field(default_factory=RiskWeights)
    api_rate_limit_per_minute: int = Field(default=1000, ge=1)
    quiet_period_start: Optional[time] = None
    quiet_period_end: Optional[time] = None
    custom_risk_thresholds: list[RiskThreshold] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class Stakeholder(BaseModel):
    stakeholder_id: UUID
    tenant_id: UUID
    email: str
    phone: Optional[str] = None
    webhook_url: Optional[str] = None
    role: Literal["Viewer", "Analyst", "Manager", "Admin"]
    mfa_secret: Optional[str] = None
    notification_channels: list[Literal["email", "sms", "webhook"]] = Field(default_factory=list)
    created_at: datetime


# ---------------------------------------------------------------------------
# Transit nodes
# ---------------------------------------------------------------------------

class TransitNodeRef(BaseModel):
    node_id: UUID
    name: str


class TransitNode(BaseModel):
    node_id: UUID
    name: str
    node_type: Literal["port", "warehouse", "distribution_center", "carrier_hub", "airport"]
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    region_id: UUID
    current_dwell_time_hours: float = Field(default=0.0, ge=0.0)
    p90_dwell_time_hours: float = Field(default=0.0, ge=0.0)
    is_disrupted: bool = False
    war_state: Literal["Safe", "Caution", "High_Risk", "Restricted"] = "Safe"


# ---------------------------------------------------------------------------
# Shipment, Route, RouteLeg
# ---------------------------------------------------------------------------

class RouteLeg(BaseModel):
    leg_id: UUID
    sequence: int = Field(ge=0)
    origin_node_id: UUID
    destination_node_id: UUID
    transport_mode: Literal["air", "sea", "rail", "road"]
    carrier_id: UUID
    estimated_duration_hours: float = Field(ge=0.0)
    estimated_cost_usd: float = Field(ge=0.0)
    carbon_kg: float = Field(ge=0.0)


class Route(BaseModel):
    route_id: UUID
    tenant_id: UUID
    shipment_id: UUID
    legs: list[RouteLeg] = Field(default_factory=list)
    total_distance_km: float = Field(ge=0.0)
    total_estimated_duration_hours: float = Field(ge=0.0)
    total_estimated_cost_usd: float = Field(ge=0.0)
    total_carbon_kg: float = Field(ge=0.0)
    is_active: bool = True
    created_at: datetime


class Shipment(BaseModel):
    shipment_id: UUID
    tenant_id: UUID
    origin: TransitNodeRef
    destination: TransitNodeRef
    active_route_id: UUID
    carrier_id: UUID
    status: Literal["In_Transit", "Delayed", "Delivered", "Connectivity_Impaired"]
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_score_updated_at: datetime
    eta: datetime
    eta_confidence_interval: tuple[datetime, datetime]
    demand_priority: Literal["Normal", "Elevated", "High"] = "Normal"
    carbon_kg: float = Field(default=0.0, ge=0.0)
    edge_agent_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_eta_confidence_interval(self) -> "Shipment":
        lower, upper = self.eta_confidence_interval
        if lower > upper:
            raise ValueError(
                f"eta_confidence_interval lower bound ({lower}) must be <= upper bound ({upper})"
            )
        return self


# ---------------------------------------------------------------------------
# Risk score history (TimescaleDB)
# ---------------------------------------------------------------------------

class RiskScoreEvent(BaseModel):
    event_id: UUID
    shipment_id: UUID
    tenant_id: UUID
    risk_score: float = Field(ge=0.0, le=100.0)
    weather_component: float = Field(ge=0.0, le=100.0)
    operational_component: float = Field(ge=0.0, le=100.0)
    war_state_component: float = Field(ge=0.0, le=100.0)
    geopolitical_component: float = Field(ge=0.0, le=100.0)
    recorded_at: datetime


# ---------------------------------------------------------------------------
# Disruption
# ---------------------------------------------------------------------------

class Disruption(BaseModel):
    disruption_id: UUID
    disruption_type: Literal[
        "weather", "carrier_delay", "port_closure", "conflict", "geopolitical", "infrastructure"
    ]
    affected_region_id: Optional[UUID] = None
    affected_node_ids: list[UUID] = Field(default_factory=list)
    severity: Literal["Low", "Medium", "High", "Critical"]
    description: str
    source: str
    started_at: datetime
    resolved_at: Optional[datetime] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Alerts & deliveries
# ---------------------------------------------------------------------------

class AlertDelivery(BaseModel):
    delivery_id: UUID
    alert_id: UUID
    stakeholder_id: UUID
    channel: Literal["email", "sms", "webhook"]
    status: Literal["delivered", "failed", "suppressed"]
    delivered_at: Optional[datetime] = None
    retry_count: int = Field(default=0, ge=0, le=3)


class Alert(BaseModel):
    alert_id: UUID
    tenant_id: UUID
    shipment_id: Optional[UUID] = None
    disruption_id: Optional[UUID] = None
    severity: Literal["Informational", "Warning", "Critical"]
    trigger_type: Literal[
        "risk_score_threshold", "risk_escalation", "war_state_change",
        "geopolitical_spike", "anomaly", "edge_offline", "no_route"
    ]
    message: str
    ai_explanation: Optional[str] = None
    created_at: datetime
    deliveries: list[AlertDelivery] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Reroute recommendation
# ---------------------------------------------------------------------------

class RerouteRecommendation(BaseModel):
    recommendation_id: UUID
    shipment_id: UUID
    tenant_id: UUID
    triggering_risk_score: float = Field(ge=0.0, le=100.0)
    disruption_id: UUID
    candidate_route: Route
    new_eta: datetime
    cost_delta_usd: float
    carbon_delta_kg: float
    rank_score: float
    status: Literal["pending", "accepted", "rejected", "auto_applied"] = "pending"
    created_at: datetime
    decided_at: Optional[datetime] = None
    decided_by: Optional[UUID] = None


# ---------------------------------------------------------------------------
# Geopolitical region
# ---------------------------------------------------------------------------

class GeopoliticalRegion(BaseModel):
    region_id: UUID
    name: str
    iso_codes: list[str] = Field(default_factory=list)
    geopolitical_risk_index: float = Field(ge=0.0, le=100.0)
    war_state: Literal["Safe", "Caution", "High_Risk", "Restricted"] = "Safe"
    risk_index_updated_at: datetime
    war_state_updated_at: datetime
    geometry: Optional[dict[str, Any]] = None  # GeoJSON


# ---------------------------------------------------------------------------
# Carrier profile
# ---------------------------------------------------------------------------

class CarrierProfile(BaseModel):
    carrier_id: UUID
    name: str
    on_time_rate_90d: float = Field(ge=0.0, le=1.0)
    on_time_rate_30d: float = Field(ge=0.0, le=1.0)
    incident_count_90d: int = Field(default=0, ge=0)
    capacity_reliability_score: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=100.0)
    is_high_risk: bool = False
    profile_updated_at: datetime


# ---------------------------------------------------------------------------
# AI interaction log
# ---------------------------------------------------------------------------

class AIInteractionLog(BaseModel):
    interaction_id: UUID
    tenant_id: UUID
    stakeholder_id: UUID
    interaction_type: Literal[
        "risk_explanation", "chatbot", "news_summary", "anomaly_explanation", "narrative_report"
    ]
    query: str
    response: str
    model_used: str
    latency_ms: int = Field(ge=0)
    fallback_used: bool = False
    timestamp: datetime


# ---------------------------------------------------------------------------
# Decision audit
# ---------------------------------------------------------------------------

class DecisionAuditEntry(BaseModel):
    entry_id: UUID
    tenant_id: UUID
    shipment_id: UUID
    decision_type: Literal["autonomous_reroute", "manual_override"]
    triggering_risk_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    recommendation_id: Optional[UUID] = None
    actor: str
    actor_role: Optional[str] = None
    previous_route_id: UUID
    new_route_id: UUID
    timestamp: datetime


# ---------------------------------------------------------------------------
# Edge agent
# ---------------------------------------------------------------------------

class EdgeAgent(BaseModel):
    agent_id: UUID
    tenant_id: UUID
    node_id: UUID
    last_heartbeat_at: datetime
    is_online: bool = True
    buffered_event_count: int = Field(default=0, ge=0)
    software_version: str = "0.1.0"


# ---------------------------------------------------------------------------
# Canonical ingestion schema
# ---------------------------------------------------------------------------

class InternalEvent(BaseModel):
    event_id: UUID
    source_type: Literal["rest", "webhook", "kafka", "sqs", "edge"]
    event_type: Literal[
        "weather_update", "carrier_update", "port_event",
        "news_event", "shipment_position", "edge_sync"
    ]
    payload: dict[str, Any]
    region_id: Optional[UUID] = None
    node_ids: list[UUID] = Field(default_factory=list)
    timestamp: datetime
    raw_source: str


# ---------------------------------------------------------------------------
# Collaboration workspace
# ---------------------------------------------------------------------------

class CollaborationMessage(BaseModel):
    message_id: UUID
    tenant_id: UUID
    shipment_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class CollaborationTask(BaseModel):
    task_id: UUID
    tenant_id: UUID
    shipment_id: UUID
    title: str
    description: Optional[str] = None
    assigned_to: Optional[UUID] = None
    status: Literal["Open", "In_Progress", "Resolved"] = "Open"
    due_date: Optional[datetime] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Digital twin
# ---------------------------------------------------------------------------

class ScenarioParameters(BaseModel):
    scenario_name: str
    node_closures: list[UUID] = Field(default_factory=list)
    conflict_zone_activations: list[UUID] = Field(default_factory=list)
    carrier_capacity_reductions: list[dict[str, Any]] = Field(default_factory=list)
    weather_events: list[dict[str, Any]] = Field(default_factory=list)


class SimulationReport(BaseModel):
    scenario_id: UUID
    tenant_id: UUID
    scenario_name: str
    parameters: ScenarioParameters
    affected_shipment_count: int = Field(ge=0)
    average_eta_deviation_hours: float
    mitigation_recommendations: list[str] = Field(default_factory=list)
    completed_at: datetime
    duration_seconds: float = Field(ge=0.0)
