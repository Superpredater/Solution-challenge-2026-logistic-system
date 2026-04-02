"""001_initial_schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

Creates all tables, TimescaleDB hypertable for risk_score_events,
composite indexes, and PostgreSQL RLS policies for tenant isolation.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None

# Tables that require RLS (tenants table is admin-only, excluded)
RLS_TABLES = [
    "stakeholders",
    "shipments",
    "routes",
    "route_legs",
    "transit_nodes",
    "risk_score_events",
    "disruptions",
    "alerts",
    "alert_deliveries",
    "reroute_recommendations",
    "geopolitical_regions",
    "carrier_profiles",
    "ai_interaction_logs",
    "decision_audit_entries",
    "edge_agents",
    "collaboration_messages",
    "collaboration_tasks",
    "scenarios",
    "simulation_reports",
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # tenants (admin-only, no RLS)
    # ------------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("eco_routing_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("autonomous_decision_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("risk_score_weights", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("api_rate_limit_per_minute", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("quiet_period_start", sa.Time(), nullable=True),
        sa.Column("quiet_period_end", sa.Time(), nullable=True),
        sa.Column("custom_risk_thresholds", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ------------------------------------------------------------------
    # stakeholders
    # ------------------------------------------------------------------
    op.create_table(
        "stakeholders",
        sa.Column("stakeholder_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("mfa_secret", sa.Text(), nullable=True),
        sa.Column("notification_channels", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_stakeholders_tenant_id", "stakeholders", ["tenant_id"])
    op.create_index("ix_stakeholders_tenant_email", "stakeholders", ["tenant_id", "email"])

    # ------------------------------------------------------------------
    # transit_nodes
    # ------------------------------------------------------------------
    op.create_table(
        "transit_nodes",
        sa.Column("node_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("node_type", sa.String(50), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_dwell_time_hours", sa.Float(), nullable=False, server_default="0"),
        sa.Column("p90_dwell_time_hours", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_disrupted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("war_state", sa.String(20), nullable=False, server_default="'Safe'"),
    )
    op.create_index("ix_transit_nodes_tenant_id", "transit_nodes", ["tenant_id"])
    op.create_index("ix_transit_nodes_region_id", "transit_nodes", ["region_id"])

    # ------------------------------------------------------------------
    # shipments
    # ------------------------------------------------------------------
    op.create_table(
        "shipments",
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("origin_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("origin_node_name", sa.String(255), nullable=False),
        sa.Column("destination_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_node_name", sa.String(255), nullable=False),
        sa.Column("active_route_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("carrier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("risk_score_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("eta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("eta_lower", sa.DateTime(timezone=True), nullable=False),
        sa.Column("eta_upper", sa.DateTime(timezone=True), nullable=False),
        sa.Column("demand_priority", sa.String(20), nullable=False, server_default="'Normal'"),
        sa.Column("carbon_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("edge_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_shipments_tenant_id", "shipments", ["tenant_id"])
    op.create_index("ix_shipments_tenant_created_at", "shipments", ["tenant_id", "created_at"])
    op.create_index("ix_shipments_tenant_status", "shipments", ["tenant_id", "status"])

    # ------------------------------------------------------------------
    # routes
    # ------------------------------------------------------------------
    op.create_table(
        "routes",
        sa.Column("route_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_distance_km", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_estimated_duration_hours", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_carbon_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_routes_tenant_id", "routes", ["tenant_id"])
    op.create_index("ix_routes_tenant_shipment", "routes", ["tenant_id", "shipment_id"])

    # ------------------------------------------------------------------
    # route_legs
    # ------------------------------------------------------------------
    op.create_table(
        "route_legs",
        sa.Column("leg_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("routes.route_id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("origin_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transport_mode", sa.String(10), nullable=False),
        sa.Column("carrier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estimated_duration_hours", sa.Float(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
        sa.Column("carbon_kg", sa.Float(), nullable=False),
    )
    op.create_index("ix_route_legs_route_id", "route_legs", ["route_id"])

    # ------------------------------------------------------------------
    # risk_score_events  (TimescaleDB hypertable)
    # ------------------------------------------------------------------
    op.create_table(
        "risk_score_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("weather_component", sa.Float(), nullable=False),
        sa.Column("operational_component", sa.Float(), nullable=False),
        sa.Column("war_state_component", sa.Float(), nullable=False),
        sa.Column("geopolitical_component", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Composite indexes for time-series queries
    op.create_index("ix_rse_shipment_recorded_at", "risk_score_events", ["shipment_id", "recorded_at"])
    op.create_index("ix_rse_tenant_recorded_at", "risk_score_events", ["tenant_id", "recorded_at"])

    # Convert to TimescaleDB hypertable partitioned by recorded_at
    op.execute(
        "SELECT create_hypertable('risk_score_events', 'recorded_at', if_not_exists => TRUE)"
    )

    # ------------------------------------------------------------------
    # disruptions
    # ------------------------------------------------------------------
    op.create_table(
        "disruptions",
        sa.Column("disruption_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("disruption_type", sa.String(30), nullable=False),
        sa.Column("affected_region_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("affected_node_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_disruptions_tenant_id", "disruptions", ["tenant_id"])
    op.create_index("ix_disruptions_tenant_created_at", "disruptions", ["tenant_id", "created_at"])

    # ------------------------------------------------------------------
    # alerts
    # ------------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("disruption_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("trigger_type", sa.String(40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alerts_tenant_id", "alerts", ["tenant_id"])
    op.create_index("ix_alerts_tenant_created_at", "alerts", ["tenant_id", "created_at"])
    op.create_index("ix_alerts_tenant_shipment", "alerts", ["tenant_id", "shipment_id"])

    # ------------------------------------------------------------------
    # alert_deliveries
    # ------------------------------------------------------------------
    op.create_table(
        "alert_deliveries",
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("alerts.alert_id", ondelete="CASCADE"), nullable=False),
        sa.Column("stakeholder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_alert_deliveries_alert_id", "alert_deliveries", ["alert_id"])
    op.create_index("ix_alert_deliveries_tenant_id", "alert_deliveries", ["tenant_id"])

    # ------------------------------------------------------------------
    # reroute_recommendations
    # ------------------------------------------------------------------
    op.create_table(
        "reroute_recommendations",
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggering_risk_score", sa.Float(), nullable=False),
        sa.Column("disruption_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_route_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("new_eta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cost_delta_usd", sa.Float(), nullable=False),
        sa.Column("carbon_delta_kg", sa.Float(), nullable=False),
        sa.Column("rank_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="'pending'"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_rr_tenant_id", "reroute_recommendations", ["tenant_id"])
    op.create_index("ix_rr_tenant_shipment", "reroute_recommendations", ["tenant_id", "shipment_id"])
    op.create_index("ix_rr_tenant_created_at", "reroute_recommendations", ["tenant_id", "created_at"])

    # ------------------------------------------------------------------
    # geopolitical_regions
    # ------------------------------------------------------------------
    op.create_table(
        "geopolitical_regions",
        sa.Column("region_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("iso_codes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("geopolitical_risk_index", sa.Float(), nullable=False),
        sa.Column("war_state", sa.String(20), nullable=False, server_default="'Safe'"),
        sa.Column("risk_index_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("war_state_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("geometry", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_geo_regions_tenant_id", "geopolitical_regions", ["tenant_id"])

    # ------------------------------------------------------------------
    # carrier_profiles
    # ------------------------------------------------------------------
    op.create_table(
        "carrier_profiles",
        sa.Column("carrier_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("on_time_rate_90d", sa.Float(), nullable=False),
        sa.Column("on_time_rate_30d", sa.Float(), nullable=False),
        sa.Column("incident_count_90d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("capacity_reliability_score", sa.Float(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("is_high_risk", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("profile_updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_carrier_profiles_tenant_id", "carrier_profiles", ["tenant_id"])

    # ------------------------------------------------------------------
    # ai_interaction_logs
    # ------------------------------------------------------------------
    op.create_table(
        "ai_interaction_logs",
        sa.Column("interaction_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stakeholder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interaction_type", sa.String(30), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_logs_tenant_id", "ai_interaction_logs", ["tenant_id"])
    op.create_index("ix_ai_logs_tenant_created_at", "ai_interaction_logs", ["tenant_id", "timestamp"])

    # ------------------------------------------------------------------
    # decision_audit_entries
    # ------------------------------------------------------------------
    op.create_table(
        "decision_audit_entries",
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_type", sa.String(30), nullable=False),
        sa.Column("triggering_risk_score", sa.Float(), nullable=True),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("actor_role", sa.String(20), nullable=True),
        sa.Column("previous_route_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("new_route_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dae_tenant_id", "decision_audit_entries", ["tenant_id"])
    op.create_index("ix_dae_tenant_shipment", "decision_audit_entries", ["tenant_id", "shipment_id"])
    op.create_index("ix_dae_tenant_created_at", "decision_audit_entries", ["tenant_id", "timestamp"])

    # ------------------------------------------------------------------
    # edge_agents
    # ------------------------------------------------------------------
    op.create_table(
        "edge_agents",
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("buffered_event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("software_version", sa.String(50), nullable=False),
    )
    op.create_index("ix_edge_agents_tenant_id", "edge_agents", ["tenant_id"])
    op.create_index("ix_edge_agents_node_id", "edge_agents", ["node_id"])

    # ------------------------------------------------------------------
    # collaboration_messages
    # ------------------------------------------------------------------
    op.create_table(
        "collaboration_messages",
        sa.Column("message_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_collab_msg_tenant_id", "collaboration_messages", ["tenant_id"])
    op.create_index("ix_collab_msg_tenant_shipment", "collaboration_messages", ["tenant_id", "shipment_id"])
    op.create_index("ix_collab_msg_tenant_created_at", "collaboration_messages", ["tenant_id", "created_at"])

    # ------------------------------------------------------------------
    # collaboration_tasks
    # ------------------------------------------------------------------
    op.create_table(
        "collaboration_tasks",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="'Open'"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_collab_task_tenant_id", "collaboration_tasks", ["tenant_id"])
    op.create_index("ix_collab_task_tenant_shipment", "collaboration_tasks", ["tenant_id", "shipment_id"])

    # ------------------------------------------------------------------
    # scenarios
    # ------------------------------------------------------------------
    op.create_table(
        "scenarios",
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_name", sa.String(255), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'pending'"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scenarios_tenant_id", "scenarios", ["tenant_id"])
    op.create_index("ix_scenarios_tenant_created_at", "scenarios", ["tenant_id", "created_at"])

    # ------------------------------------------------------------------
    # simulation_reports
    # ------------------------------------------------------------------
    op.create_table(
        "simulation_reports",
        sa.Column("report_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_name", sa.String(255), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("affected_shipment_count", sa.Integer(), nullable=False),
        sa.Column("average_eta_deviation_hours", sa.Float(), nullable=False),
        sa.Column("mitigation_recommendations", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
    )
    op.create_index("ix_sim_reports_tenant_id", "simulation_reports", ["tenant_id"])
    op.create_index("ix_sim_reports_scenario_id", "simulation_reports", ["scenario_id"])

    # ------------------------------------------------------------------
    # Row-Level Security policies
    # ------------------------------------------------------------------
    for table in RLS_TABLES:
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # Tenant isolation policy
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id::text = current_setting('app.tenant_id', true))"
        )

        # Superuser bypass policy for migration user and service accounts
        op.execute(
            f"CREATE POLICY superuser_bypass ON {table} "
            f"TO postgres "
            f"USING (true)"
        )


def downgrade() -> None:
    # Drop RLS policies first
    for table in reversed(RLS_TABLES):
        op.execute(f"DROP POLICY IF EXISTS superuser_bypass ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop tables in reverse dependency order
    op.drop_table("simulation_reports")
    op.drop_table("scenarios")
    op.drop_table("collaboration_tasks")
    op.drop_table("collaboration_messages")
    op.drop_table("edge_agents")
    op.drop_table("decision_audit_entries")
    op.drop_table("ai_interaction_logs")
    op.drop_table("carrier_profiles")
    op.drop_table("geopolitical_regions")
    op.drop_table("reroute_recommendations")
    op.drop_table("alert_deliveries")
    op.drop_table("alerts")
    op.drop_table("disruptions")
    op.drop_table("risk_score_events")
    op.drop_table("route_legs")
    op.drop_table("routes")
    op.drop_table("shipments")
    op.drop_table("transit_nodes")
    op.drop_table("stakeholders")
    op.drop_table("tenants")
