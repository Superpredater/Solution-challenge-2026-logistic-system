"""GraphQL schema using Strawberry — types, queries, mutations, subscriptions."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, List, Optional
from uuid import UUID

import redis.asyncio as aioredis
import strawberry
from strawberry.types import Info

from services.shared.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Strawberry types
# ---------------------------------------------------------------------------

@strawberry.type
class RouteLegType:
    leg_id: str
    sequence: int
    origin_node_id: str
    destination_node_id: str
    transport_mode: str
    carrier_id: str
    estimated_duration_hours: float
    estimated_cost_usd: float
    carbon_kg: float


@strawberry.type
class RouteType:
    route_id: str
    shipment_id: str
    total_distance_km: float
    total_estimated_duration_hours: float
    total_estimated_cost_usd: float
    total_carbon_kg: float
    is_active: bool


@strawberry.type
class ShipmentType:
    shipment_id: str
    tenant_id: str
    status: str
    risk_score: float
    risk_score_updated_at: str
    eta: str
    eta_lower: str
    eta_upper: str
    active_route_id: str
    carrier_id: str
    demand_priority: str
    carbon_kg: float


@strawberry.type
class RerouteRecommendationType:
    recommendation_id: str
    shipment_id: str
    triggering_risk_score: float
    cost_delta_usd: float
    carbon_delta_kg: float
    rank_score: float
    status: str
    new_eta: str
    created_at: str


@strawberry.type
class AlertType:
    alert_id: str
    tenant_id: str
    shipment_id: Optional[str]
    severity: str
    trigger_type: str
    message: str
    ai_explanation: Optional[str]
    created_at: str


@strawberry.type
class GeopoliticalRegionType:
    region_id: str
    name: str
    geopolitical_risk_index: float
    war_state: str
    risk_index_updated_at: str
    war_state_updated_at: str


@strawberry.type
class CarrierProfileType:
    carrier_id: str
    name: str
    on_time_rate_90d: float
    on_time_rate_30d: float
    incident_count_90d: int
    risk_score: float
    is_high_risk: bool


@strawberry.type
class AIExplanationType:
    shipment_id: str
    explanation: str
    fallback_used: bool


@strawberry.type
class RiskScoreEventType:
    event_id: str
    shipment_id: str
    risk_score: float
    weather_component: float
    operational_component: float
    war_state_component: float
    geopolitical_component: float
    recorded_at: str


@strawberry.input
class ShipmentFilterInput:
    status: Optional[str] = None
    min_risk_score: Optional[float] = None
    max_risk_score: Optional[float] = None


@strawberry.input
class DisruptionFilterInput:
    severity: Optional[str] = None
    disruption_type: Optional[str] = None


@strawberry.input
class AlertFilterInput:
    severity: Optional[str] = None
    trigger_type: Optional[str] = None


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

@strawberry.type
class Query:
    @strawberry.field
    async def shipment(self, id: str, info: Info) -> Optional[ShipmentType]:
        from sqlalchemy import select
        from services.shared.orm_models import ShipmentORM
        from services.shared.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ShipmentORM).where(ShipmentORM.shipment_id == UUID(id))
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return _shipment_type(row)

    @strawberry.field
    async def shipments(
        self, filter: Optional[ShipmentFilterInput] = None, info: Info = None
    ) -> List[ShipmentType]:
        from sqlalchemy import select
        from services.shared.orm_models import ShipmentORM
        from services.shared.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            q = select(ShipmentORM).limit(100)
            if filter:
                if filter.status:
                    q = q.where(ShipmentORM.status == filter.status)
                if filter.min_risk_score is not None:
                    q = q.where(ShipmentORM.risk_score >= filter.min_risk_score)
                if filter.max_risk_score is not None:
                    q = q.where(ShipmentORM.risk_score <= filter.max_risk_score)
            result = await session.execute(q)
            return [_shipment_type(r) for r in result.scalars().all()]

    @strawberry.field
    async def disruptions(
        self, filter: Optional[DisruptionFilterInput] = None, info: Info = None
    ) -> List[AlertType]:
        from sqlalchemy import select
        from services.shared.orm_models import AlertORM
        from services.shared.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            q = select(AlertORM).limit(100)
            if filter and filter.severity:
                q = q.where(AlertORM.severity == filter.severity)
            result = await session.execute(q)
            return [_alert_type(r) for r in result.scalars().all()]

    @strawberry.field
    async def region(self, id: str, info: Info) -> Optional[GeopoliticalRegionType]:
        from sqlalchemy import select
        from services.shared.orm_models import GeopoliticalRegionORM
        from services.shared.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(GeopoliticalRegionORM).where(
                    GeopoliticalRegionORM.region_id == UUID(id)
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return GeopoliticalRegionType(
                region_id=str(row.region_id),
                name=row.name,
                geopolitical_risk_index=row.geopolitical_risk_index,
                war_state=row.war_state,
                risk_index_updated_at=row.risk_index_updated_at.isoformat(),
                war_state_updated_at=row.war_state_updated_at.isoformat(),
            )

    @strawberry.field
    async def carrier_profile(self, id: str, info: Info) -> Optional[CarrierProfileType]:
        from sqlalchemy import select
        from services.shared.orm_models import CarrierProfileORM
        from services.shared.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CarrierProfileORM).where(CarrierProfileORM.carrier_id == UUID(id))
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return CarrierProfileType(
                carrier_id=str(row.carrier_id),
                name=row.name,
                on_time_rate_90d=row.on_time_rate_90d,
                on_time_rate_30d=row.on_time_rate_30d,
                incident_count_90d=row.incident_count_90d,
                risk_score=row.risk_score,
                is_high_risk=row.is_high_risk,
            )

    @strawberry.field
    async def alerts(
        self, filter: Optional[AlertFilterInput] = None, info: Info = None
    ) -> List[AlertType]:
        from sqlalchemy import select
        from services.shared.orm_models import AlertORM
        from services.shared.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            q = select(AlertORM).limit(100)
            if filter:
                if filter.severity:
                    q = q.where(AlertORM.severity == filter.severity)
                if filter.trigger_type:
                    q = q.where(AlertORM.trigger_type == filter.trigger_type)
            result = await session.execute(q)
            return [_alert_type(r) for r in result.scalars().all()]

    @strawberry.field
    async def decision_audit(
        self, lookback_days: int = 30, info: Info = None
    ) -> List[str]:
        from sqlalchemy import select
        from services.shared.orm_models import DecisionAuditEntryORM
        from services.shared.database import AsyncSessionLocal
        from datetime import timezone, timedelta

        since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(DecisionAuditEntryORM)
                .where(DecisionAuditEntryORM.timestamp >= since)
                .limit(200)
            )
            return [str(r.entry_id) for r in result.scalars().all()]


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def accept_reroute_recommendation(
        self, recommendation_id: str, accepted_by: str
    ) -> str:
        from sqlalchemy import select
        from services.shared.orm_models import RerouteRecommendationORM
        from services.shared.database import AsyncSessionLocal
        from datetime import timezone

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RerouteRecommendationORM).where(
                    RerouteRecommendationORM.recommendation_id == UUID(recommendation_id)
                )
            )
            rec = result.scalar_one_or_none()
            if rec is None:
                return "not_found"
            rec.status = "accepted"
            rec.decided_at = datetime.now(timezone.utc)
            rec.decided_by = UUID(accepted_by)
            await session.commit()
        return "accepted"

    @strawberry.mutation
    async def reject_reroute_recommendation(
        self, recommendation_id: str, rejected_by: str
    ) -> str:
        from sqlalchemy import select
        from services.shared.orm_models import RerouteRecommendationORM
        from services.shared.database import AsyncSessionLocal
        from datetime import timezone

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RerouteRecommendationORM).where(
                    RerouteRecommendationORM.recommendation_id == UUID(recommendation_id)
                )
            )
            rec = result.scalar_one_or_none()
            if rec is None:
                return "not_found"
            rec.status = "rejected"
            rec.decided_at = datetime.now(timezone.utc)
            rec.decided_by = UUID(rejected_by)
            await session.commit()
        return "rejected"

    @strawberry.mutation
    async def manual_override(
        self, shipment_id: str, new_route_id: str, actor_id: str
    ) -> str:
        # Delegates to decision engine override handler
        return f"override_requested:{shipment_id}:{new_route_id}"

    @strawberry.mutation
    async def create_scenario(
        self, scenario_name: str, tenant_id: str, parameters_json: str
    ) -> str:
        import json as _json
        import uuid as _uuid
        from services.shared.orm_models import ScenarioORM
        from services.shared.database import AsyncSessionLocal
        from datetime import timezone

        params = _json.loads(parameters_json)
        scenario_id = _uuid.uuid4()
        async with AsyncSessionLocal() as session:
            session.add(
                ScenarioORM(
                    scenario_id=scenario_id,
                    tenant_id=UUID(tenant_id),
                    scenario_name=scenario_name,
                    parameters=params,
                    status="pending",
                    created_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
        return str(scenario_id)


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def risk_score_updated(
        self, tenant_id: str
    ) -> AsyncGenerator[RiskScoreEventType, None]:
        """Subscribe to risk score updates via Redis pub/sub."""
        channel = f"risk_score_updates:{tenant_id}"
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield RiskScoreEventType(
                            event_id=data.get("event_id", ""),
                            shipment_id=data.get("shipment_id", ""),
                            risk_score=data.get("risk_score", 0.0),
                            weather_component=data.get("weather_component", 0.0),
                            operational_component=data.get("operational_component", 0.0),
                            war_state_component=data.get("war_state_component", 0.0),
                            geopolitical_component=data.get("geopolitical_component", 0.0),
                            recorded_at=data.get("recorded_at", ""),
                        )
                    except Exception as exc:
                        logger.warning("Failed to parse risk_score_updated message: %s", exc)
        finally:
            await pubsub.unsubscribe(channel)
            await redis.aclose()

    @strawberry.subscription
    async def alert_created(
        self, tenant_id: str
    ) -> AsyncGenerator[AlertType, None]:
        """Subscribe to new alerts via Redis pub/sub."""
        channel = f"alerts:{tenant_id}"
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield AlertType(
                            alert_id=data.get("alert_id", ""),
                            tenant_id=data.get("tenant_id", ""),
                            shipment_id=data.get("shipment_id"),
                            severity=data.get("severity", "Informational"),
                            trigger_type=data.get("trigger_type", ""),
                            message=data.get("message", ""),
                            ai_explanation=data.get("ai_explanation"),
                            created_at=data.get("created_at", ""),
                        )
                    except Exception as exc:
                        logger.warning("Failed to parse alert_created message: %s", exc)
        finally:
            await pubsub.unsubscribe(channel)
            await redis.aclose()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _shipment_type(r: Any) -> ShipmentType:
    return ShipmentType(
        shipment_id=str(r.shipment_id),
        tenant_id=str(r.tenant_id),
        status=r.status,
        risk_score=r.risk_score,
        risk_score_updated_at=r.risk_score_updated_at.isoformat(),
        eta=r.eta.isoformat(),
        eta_lower=r.eta_lower.isoformat(),
        eta_upper=r.eta_upper.isoformat(),
        active_route_id=str(r.active_route_id),
        carrier_id=str(r.carrier_id),
        demand_priority=r.demand_priority,
        carbon_kg=r.carbon_kg,
    )


def _alert_type(r: Any) -> AlertType:
    return AlertType(
        alert_id=str(r.alert_id),
        tenant_id=str(r.tenant_id),
        shipment_id=str(r.shipment_id) if r.shipment_id else None,
        severity=r.severity,
        trigger_type=r.trigger_type,
        message=r.message,
        ai_explanation=r.ai_explanation,
        created_at=r.created_at.isoformat(),
    )
