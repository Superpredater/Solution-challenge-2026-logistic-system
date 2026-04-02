"""Scheduled recalculator — ensures all active shipments are scored every 15 minutes."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.database import get_db_session as get_session
from services.shared.kafka import publish
from services.shared.orm_models import ShipmentORM

logger = logging.getLogger(__name__)

RECALC_INTERVAL_SECONDS = 15 * 60  # 15 minutes
RISK_UPDATES_TOPIC = "risk.score.updates"


class ScheduledRecalculator:
    """Periodically recalculates risk scores for all active shipments."""

    async def run(self, session: AsyncSession) -> None:
        """Query active shipments and publish recalculation triggers."""
        result = await session.execute(
            select(ShipmentORM).where(ShipmentORM.status.in_(["In_Transit", "Delayed"]))
        )
        shipments = result.scalars().all()
        logger.info("Scheduled recalculation: %d active shipments", len(shipments))

        for shipment in shipments:
            await publish(
                RISK_UPDATES_TOPIC,
                {
                    "event": "scheduled_recalc",
                    "shipment_id": str(shipment.shipment_id),
                    "tenant_id": str(shipment.tenant_id),
                    "current_risk_score": float(shipment.risk_score or 0.0),
                },
            )

    async def start_background_task(self) -> None:
        """Run the recalculator every 15 minutes as an asyncio background task."""
        while True:
            try:
                async with get_session() as session:
                    await self.run(session)
            except Exception as exc:  # noqa: BLE001
                logger.error("Scheduled recalculator error: %s", exc)
            await asyncio.sleep(RECALC_INTERVAL_SECONDS)
