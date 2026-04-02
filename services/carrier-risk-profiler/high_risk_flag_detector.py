"""Detects and clears high-risk flags on carrier profiles."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.kafka import publish
from services.shared.orm_models import CarrierProfileORM
from .performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)

HIGH_RISK_THRESHOLD = 0.80
ALERTS_TOPIC = "carrier.high_risk.alerts"


class HighRiskFlagDetector:
    """Monitors 30-day on-time rate and manages the is_high_risk flag."""

    def __init__(self) -> None:
        self._tracker = PerformanceTracker()

    async def check_and_flag(self, carrier_id: UUID, session: AsyncSession) -> None:
        """
        If the 30-day on-time rate drops below 80%, set is_high_risk=True
        and publish an admin notification.
        """
        rate_30d = await self._tracker.get_on_time_rate(carrier_id, 30, session)

        if rate_30d < HIGH_RISK_THRESHOLD:
            await session.execute(
                update(CarrierProfileORM)
                .where(CarrierProfileORM.carrier_id == carrier_id)
                .values(
                    is_high_risk=True,
                    profile_updated_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

            await publish(
                ALERTS_TOPIC,
                {
                    "event": "carrier_high_risk_flagged",
                    "carrier_id": str(carrier_id),
                    "on_time_rate_30d": rate_30d,
                    "threshold": HIGH_RISK_THRESHOLD,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            logger.warning(
                "Carrier %s flagged as high-risk (30d rate=%.2f)", carrier_id, rate_30d
            )

    async def clear_flag_if_recovered(
        self, carrier_id: UUID, session: AsyncSession
    ) -> None:
        """Clear the high-risk flag if the 30-day rate has recovered above 80%."""
        rate_30d = await self._tracker.get_on_time_rate(carrier_id, 30, session)

        if rate_30d >= HIGH_RISK_THRESHOLD:
            result = await session.execute(
                select(CarrierProfileORM).where(
                    CarrierProfileORM.carrier_id == carrier_id,
                    CarrierProfileORM.is_high_risk.is_(True),
                )
            )
            profile = result.scalar_one_or_none()
            if profile is not None:
                await session.execute(
                    update(CarrierProfileORM)
                    .where(CarrierProfileORM.carrier_id == carrier_id)
                    .values(
                        is_high_risk=False,
                        profile_updated_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()
                logger.info(
                    "Carrier %s high-risk flag cleared (30d rate=%.2f)", carrier_id, rate_30d
                )
