"""Autonomous rerouting executor."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.kafka import publish
from services.shared.models import RerouteRecommendation, Tenant
from services.shared.orm_models import ShipmentORM

logger = logging.getLogger(__name__)

TOPIC = "shipment.route.updates"


class AutonomousExecutor:
    """Apply recommendations automatically when autonomous mode is enabled."""

    async def execute(
        self,
        recommendation: RerouteRecommendation,
        tenant: Tenant,
        session: AsyncSession,
    ) -> bool:
        if not tenant.autonomous_decision_enabled:
            return False
        if recommendation.triggering_risk_score <= 70:
            return False

        await session.execute(
            update(ShipmentORM)
            .where(ShipmentORM.shipment_id == recommendation.shipment_id)
            .values(
                active_route_id=recommendation.candidate_route.route_id,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        await publish(
            TOPIC,
            {
                "event": "autonomous_reroute",
                "shipment_id": str(recommendation.shipment_id),
                "new_route_id": str(recommendation.candidate_route.route_id),
                "recommendation_id": str(recommendation.recommendation_id),
                "triggering_risk_score": recommendation.triggering_risk_score,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            key=str(recommendation.shipment_id),
        )
        logger.info(
            "Autonomous reroute applied for shipment %s (risk=%.1f)",
            recommendation.shipment_id,
            recommendation.triggering_risk_score,
        )
        return True
