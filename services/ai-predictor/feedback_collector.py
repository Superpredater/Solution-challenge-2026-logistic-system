"""Collect actual delivery timestamps as ETA model feedback."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Write ETA feedback records to the eta_feedback table."""

    async def collect(
        self,
        shipment_id: UUID,
        actual_delivery: datetime,
        session: AsyncSession,
    ) -> None:
        await session.execute(
            text(
                "INSERT INTO eta_feedback (id, shipment_id, actual_delivery, recorded_at) "
                "VALUES (:id, :shipment_id, :actual_delivery, :recorded_at)"
            ),
            {
                "id": uuid.uuid4(),
                "shipment_id": shipment_id,
                "actual_delivery": actual_delivery,
                "recorded_at": datetime.now(timezone.utc),
            },
        )
        await session.commit()
        logger.debug("ETA feedback recorded for shipment %s", shipment_id)
