"""SQLAlchemy 2 ORM models for the Smart Supply Chain Optimization platform.

All tenant-scoped tables include a `tenant_id` UUID column for PostgreSQL
Row-Level Security (RLS) enforcement.  The `risk_score_events` table is
marked for TimescaleDB hypertable conversion in the Alembic migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# ---------------------------------------------------------------------------
# Tenants (admin-only, no RLS)
# ---------------------------------------------------------------------------

class TenantORM(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    eco_routing_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    autonomous_decision_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    risk_score_weights: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    api_rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    quiet_period_start: Mapped[Optional[time]] = mapped_column(nullable=True)
    quiet_period_end: Mapped[Optional[time]] = mapped_column(nullable=True)
    custom_risk_thresholds: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Stakeholders
# ---------------------------------------------------------------------------

class StakeholderORM(Base):
    __tablename__ = "stakeholders"
    __table_args__ = (
        Index("ix_stakeholders_tenant_id", "tenant_id"),
        Index("ix_stakeholders_tenant_email", "tenant_id", "email"),
    )

    stakeholder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notification_channels: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Transit nodes
# ---------------------------------------------------------------------------

class TransitNodeORM(Base):
    __tablename__ = "transit_nodes"
    __table_args__ = (
        Index("ix_transit_nodes_tenant_id", "tenant_id"),
        Index("ix_transit_nodes_region_id", "region_id"),
    )

    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    region_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    current_dwell_time_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    p90_dwell_time_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_disrupted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    war_state: Mapped[str] = mapped_column(String(20), default="Safe", nullable=False)


# ---------------------------------------------------------------------------
# Shipments
# ---------------------------------------------------------------------------

class ShipmentORM(Base):
    __tablename__ = "shipments"
    __table_args__ = (
        Index("ix_shipments_tenant_id", "tenant_id"),
        Index("ix_shipments_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_shipments_tenant_status", "tenant_id", "status"),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    origin_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    origin_node_name: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    destination_node_name: Mapped[str] = mapped_column(String(255), nullable=False)
    active_route_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    carrier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_score_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eta_lower: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eta_upper: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    demand_priority: Mapped[str] = mapped_column(String(20), default="Normal", nullable=False)
    carbon_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    edge_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Routes & legs
# ---------------------------------------------------------------------------

class RouteORM(Base):
    __tablename__ = "routes"
    __table_args__ = (
        Index("ix_routes_tenant_id", "tenant_id"),
        Index("ix_routes_tenant_shipment", "tenant_id", "shipment_id"),
    )

    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    shipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    total_distance_km: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_estimated_duration_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_carbon_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    legs: Mapped[list["RouteLegORM"]] = relationship(
        "RouteLegORM", back_populates="route", cascade="all, delete-orphan"
    )


class RouteLegORM(Base):
    __tablename__ = "route_legs"
    __table_args__ = (
        Index("ix_route_legs_route_id", "route_id"),
    )

    leg_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.route_id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    origin_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    destination_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    transport_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    carrier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    estimated_duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    carbon_kg: Mapped[float] = mapped_column(Float, nullable=False)

    route: Mapped["RouteORM"] = relationship("RouteORM", back_populates="legs")


# ---------------------------------------------------------------------------
# Risk score events (TimescaleDB hypertable on recorded_at)
# ---------------------------------------------------------------------------

class RiskScoreEventORM(Base):
    __tablename__ = "risk_score_events"
    __table_args__ = (
        Index("ix_rse_shipment_recorded_at", "shipment_id", "recorded_at"),
        Index("ix_rse_tenant_recorded_at", "tenant_id", "recorded_at"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    weather_component: Mapped[float] = mapped_column(Float, nullable=False)
    operational_component: Mapped[float] = mapped_column(Float, nullable=False)
    war_state_component: Mapped[float] = mapped_column(Float, nullable=False)
    geopolitical_component: Mapped[float] = mapped_column(Float, nullable=False)
    # TimescaleDB partition key
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Disruptions
# ---------------------------------------------------------------------------

class DisruptionORM(Base):
    __tablename__ = "disruptions"
    __table_args__ = (
        Index("ix_disruptions_tenant_id", "tenant_id"),
        Index("ix_disruptions_tenant_created_at", "tenant_id", "created_at"),
    )

    disruption_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    disruption_type: Mapped[str] = mapped_column(String(30), nullable=False)
    affected_region_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    affected_node_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Alerts & deliveries
# ---------------------------------------------------------------------------

class AlertORM(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_tenant_id", "tenant_id"),
        Index("ix_alerts_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_alerts_tenant_shipment", "tenant_id", "shipment_id"),
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    shipment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    disruption_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    deliveries: Mapped[list["AlertDeliveryORM"]] = relationship(
        "AlertDeliveryORM", back_populates="alert", cascade="all, delete-orphan"
    )


class AlertDeliveryORM(Base):
    __tablename__ = "alert_deliveries"
    __table_args__ = (
        Index("ix_alert_deliveries_alert_id", "alert_id"),
        Index("ix_alert_deliveries_tenant_id", "tenant_id"),
    )

    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.alert_id", ondelete="CASCADE"), nullable=False
    )
    stakeholder_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    alert: Mapped["AlertORM"] = relationship("AlertORM", back_populates="deliveries")


# ---------------------------------------------------------------------------
# Reroute recommendations
# ---------------------------------------------------------------------------

class RerouteRecommendationORM(Base):
    __tablename__ = "reroute_recommendations"
    __table_args__ = (
        Index("ix_rr_tenant_id", "tenant_id"),
        Index("ix_rr_tenant_shipment", "tenant_id", "shipment_id"),
        Index("ix_rr_tenant_created_at", "tenant_id", "created_at"),
    )

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    triggering_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    disruption_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    candidate_route_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    new_eta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cost_delta_usd: Mapped[float] = mapped_column(Float, nullable=False)
    carbon_delta_kg: Mapped[float] = mapped_column(Float, nullable=False)
    rank_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)


# ---------------------------------------------------------------------------
# Geopolitical regions
# ---------------------------------------------------------------------------

class GeopoliticalRegionORM(Base):
    __tablename__ = "geopolitical_regions"
    __table_args__ = (
        Index("ix_geo_regions_tenant_id", "tenant_id"),
    )

    region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    iso_codes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    geopolitical_risk_index: Mapped[float] = mapped_column(Float, nullable=False)
    war_state: Mapped[str] = mapped_column(String(20), default="Safe", nullable=False)
    risk_index_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    war_state_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    geometry: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


# ---------------------------------------------------------------------------
# Carrier profiles
# ---------------------------------------------------------------------------

class CarrierProfileORM(Base):
    __tablename__ = "carrier_profiles"
    __table_args__ = (
        Index("ix_carrier_profiles_tenant_id", "tenant_id"),
    )

    carrier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    on_time_rate_90d: Mapped[float] = mapped_column(Float, nullable=False)
    on_time_rate_30d: Mapped[float] = mapped_column(Float, nullable=False)
    incident_count_90d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    capacity_reliability_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_high_risk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    profile_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# AI interaction logs
# ---------------------------------------------------------------------------

class AIInteractionLogORM(Base):
    __tablename__ = "ai_interaction_logs"
    __table_args__ = (
        Index("ix_ai_logs_tenant_id", "tenant_id"),
        Index("ix_ai_logs_tenant_created_at", "tenant_id", "timestamp"),
    )

    interaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    stakeholder_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Decision audit entries
# ---------------------------------------------------------------------------

class DecisionAuditEntryORM(Base):
    __tablename__ = "decision_audit_entries"
    __table_args__ = (
        Index("ix_dae_tenant_id", "tenant_id"),
        Index("ix_dae_tenant_shipment", "tenant_id", "shipment_id"),
        Index("ix_dae_tenant_created_at", "tenant_id", "timestamp"),
    )

    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    shipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(30), nullable=False)
    triggering_risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommendation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    previous_route_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    new_route_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Edge agents
# ---------------------------------------------------------------------------

class EdgeAgentORM(Base):
    __tablename__ = "edge_agents"
    __table_args__ = (
        Index("ix_edge_agents_tenant_id", "tenant_id"),
        Index("ix_edge_agents_node_id", "node_id"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    buffered_event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    software_version: Mapped[str] = mapped_column(String(50), nullable=False)


# ---------------------------------------------------------------------------
# Collaboration workspace
# ---------------------------------------------------------------------------

class CollaborationMessageORM(Base):
    __tablename__ = "collaboration_messages"
    __table_args__ = (
        Index("ix_collab_msg_tenant_id", "tenant_id"),
        Index("ix_collab_msg_tenant_shipment", "tenant_id", "shipment_id"),
        Index("ix_collab_msg_tenant_created_at", "tenant_id", "created_at"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    shipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CollaborationTaskORM(Base):
    __tablename__ = "collaboration_tasks"
    __table_args__ = (
        Index("ix_collab_task_tenant_id", "tenant_id"),
        Index("ix_collab_task_tenant_shipment", "tenant_id", "shipment_id"),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    shipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Open", nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Digital twin scenarios & reports
# ---------------------------------------------------------------------------

class ScenarioORM(Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        Index("ix_scenarios_tenant_id", "tenant_id"),
        Index("ix_scenarios_tenant_created_at", "tenant_id", "created_at"),
    )

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SimulationReportORM(Base):
    __tablename__ = "simulation_reports"
    __table_args__ = (
        Index("ix_sim_reports_tenant_id", "tenant_id"),
        Index("ix_sim_reports_scenario_id", "scenario_id"),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    affected_shipment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    average_eta_deviation_hours: Mapped[float] = mapped_column(Float, nullable=False)
    mitigation_recommendations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)


# ---------------------------------------------------------------------------
# Geopolitical risk history (TimescaleDB hypertable on recorded_at)
# ---------------------------------------------------------------------------

class GeopoliticalRiskHistoryORM(Base):
    __tablename__ = "geopolitical_risk_history"
    __table_args__ = (
        Index("ix_geo_risk_history_region_recorded_at", "region_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    region_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    risk_index: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# API analytics (TimescaleDB hypertable on recorded_at)
# Migration snippet:
#   SELECT create_hypertable('api_analytics', 'recorded_at', if_not_exists => TRUE);
# ---------------------------------------------------------------------------

class APIAnalyticsORM(Base):
    __tablename__ = "api_analytics"
    __table_args__ = (
        Index("ix_api_analytics_tenant_recorded_at", "tenant_id", "recorded_at"),
        Index("ix_api_analytics_api_key_recorded_at", "api_key", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ---------------------------------------------------------------------------
# Carrier delivery records (for rolling performance metrics)
# ---------------------------------------------------------------------------

class CarrierDeliveryORM(Base):
    __tablename__ = "carrier_deliveries"
    __table_args__ = (
        Index("ix_carrier_deliveries_carrier_recorded_at", "carrier_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    carrier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    on_time: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
