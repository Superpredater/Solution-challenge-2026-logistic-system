"""Manual override handler for shipment routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.kafka import publish
from services.shared.orm_models import ShipmentORM

logger = logging.getLogger(__name__)

TOPIC = "shipment.route.updates"


class OverrideHandler:
    """Apply a manual route override and publish the event."""

    async def apply_override(
        self,
        shipment_id: UUID,
        new_route_id: UUID,
        actor_id: str,
        actor_role: str,
        session: AsyncSession,
    ) -> None:
        result = await session.execute(
            select(ShipmentORM.active_route_id).where(
                ShipmentORM.shipment_id == shipment_id
            )
        )
        row = result.one_or_none()
        previous_route_id = row[0] if row else None

        await session.execute(
            update(ShipmentORM)
            .where(ShipmentORM.shipment_id == shipment_id)
            .values(
                active_route_id=new_route_id,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        await publish(
            TOPIC,
            {
                "event": "manual_override",
                "shipment_id": str(shipment_id),
                "previous_route_id": str(previous_route_id) if previous_route_id else None,
                "new_route_id": str(new_route_id),
                "actor_id": actor_id,
                "actor_role": actor_role,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            key=str(shipment_id),
        )
        logger.info(
            "Manual override applied for shipment %s by %s (%s)",
            shipment_id, actor_id, actor_role,
        )
