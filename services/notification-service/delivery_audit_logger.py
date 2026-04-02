"""Persist alert delivery records to the database."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.models import AlertDelivery
from services.shared.orm_models import AlertDeliveryORM

logger = logging.getLogger(__name__)


class DeliveryAuditLogger:
    """Write AlertDelivery records to alert_deliveries table."""

    async def log(self, delivery: AlertDelivery, session: AsyncSession) -> None:
        orm = AlertDeliveryORM(
            delivery_id=delivery.delivery_id,
            tenant_id=None,  # populated from alert context in production
            alert_id=delivery.alert_id,
            stakeholder_id=delivery.stakeholder_id,
            channel=delivery.channel,
            status=delivery.status,
            delivered_at=delivery.delivered_at,
            retry_count=delivery.retry_count,
        )
        session.add(orm)
        await session.commit()
        logger.debug("Delivery %s logged", delivery.delivery_id)
