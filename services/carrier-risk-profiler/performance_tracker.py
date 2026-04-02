"""Tracks rolling carrier delivery performance metrics."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.orm_models import CarrierDeliveryORM, CarrierProfileORM

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Maintains rolling on-time delivery rate and incident history per carrier."""

    async def update_delivery(
        self, carrier_id: UUID, on_time: bool, session: AsyncSession
    ) -> None:
        """Record a delivery outcome and refresh rolling metrics on the carrier profile."""
        row = CarrierDeliveryORM(
            carrier_id=carrier_id,
            on_time=on_time,
            recorded_at=datetime.now(timezone.utc),
        )
        session.add(row)

        # Refresh 90-day and 30-day rates on the profile
        rate_90d = await self.get_on_time_rate(carrier_id, 90, session)
        rate_30d = await self.get_on_time_rate(carrier_id, 30, session)
        incidents_90d = await self.get_incident_count(carrier_id, 90, session)

        await session.execute(
            update(CarrierProfileORM)
            .where(CarrierProfileORM.carrier_id == carrier_id)
            .values(
                on_time_rate_90d=rate_90d,
                on_time_rate_30d=rate_30d,
                incident_count_90d=incidents_90d,
                profile_updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
        logger.debug("Carrier %s delivery updated (on_time=%s)", carrier_id, on_time)

    async def get_on_time_rate(
        self, carrier_id: UUID, days: int, session: AsyncSession
    ) -> float:
        """Return the on-time delivery rate over the last *days* days (0.0–1.0)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await session.execute(
            select(
                func.count().label("total"),
                func.sum(
                    func.cast(CarrierDeliveryORM.on_time, type_=None)
                ).label("on_time_count"),
            ).where(
                CarrierDeliveryORM.carrier_id == carrier_id,
                CarrierDeliveryORM.recorded_at >= cutoff,
            )
        )
        row = result.one()
        total = row.total or 0
        on_time_count = row.on_time_count or 0
        return float(on_time_count) / float(total) if total > 0 else 1.0

    async def get_incident_count(
        self, carrier_id: UUID, days: int, session: AsyncSession
    ) -> int:
        """Return the number of late deliveries (incidents) in the last *days* days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await session.execute(
            select(func.count()).where(
                CarrierDeliveryORM.carrier_id == carrier_id,
                CarrierDeliveryORM.recorded_at >= cutoff,
                CarrierDeliveryORM.on_time.is_(False),
            )
        )
        return result.scalar_one() or 0
