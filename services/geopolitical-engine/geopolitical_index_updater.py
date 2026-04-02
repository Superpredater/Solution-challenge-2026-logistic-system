"""Updates Geopolitical_Risk_Index and detects spikes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.kafka import publish
from services.shared.orm_models import GeopoliticalRegionORM, GeopoliticalRiskHistoryORM
from .region_registry import RegionRegistry

logger = logging.getLogger(__name__)

SPIKE_THRESHOLD = 20.0
SPIKE_WINDOW_HOURS = 24
RISK_UPDATES_TOPIC = "geopolitical.risk.updates"


class GeopoliticalIndexUpdater:
    """Maintains per-region Geopolitical_Risk_Index and detects 24-hour spikes."""

    def __init__(self) -> None:
        self._registry = RegionRegistry()

    async def update(
        self, region_id: UUID, signal: dict, session: AsyncSession
    ) -> None:
        """
        Adjust the region's Geopolitical_Risk_Index based on signal severity,
        persist the new value, and record a history entry.
        """
        region = await self._registry.get_region(region_id, session)
        severity: float = float(signal.get("severity", 0.0))

        # Blend: new_index = clamp(current + severity * 30, 0, 100)
        delta = severity * 30.0
        new_index = max(0.0, min(100.0, region.geopolitical_risk_index + delta))

        await self._registry.update_risk_index(region_id, new_index, session)

        # Persist history for spike detection
        history_row = GeopoliticalRiskHistoryORM(
            region_id=region_id,
            risk_index=new_index,
            recorded_at=datetime.now(timezone.utc),
        )
        session.add(history_row)
        await session.commit()

        logger.info(
            "Region %s risk index: %.1f → %.1f (delta=%.1f)",
            region_id, region.geopolitical_risk_index, new_index, delta,
        )

    async def check_spike(self, region_id: UUID, session: AsyncSession) -> bool:
        """
        Returns True if the Geopolitical_Risk_Index increased ≥ 20 points
        in the last 24 hours.  On spike, publishes to geopolitical.risk.updates.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=SPIKE_WINDOW_HOURS)
        result = await session.execute(
            select(GeopoliticalRiskHistoryORM)
            .where(
                GeopoliticalRiskHistoryORM.region_id == region_id,
                GeopoliticalRiskHistoryORM.recorded_at >= cutoff,
            )
            .order_by(GeopoliticalRiskHistoryORM.recorded_at.asc())
        )
        rows = result.scalars().all()
        if len(rows) < 2:
            return False

        earliest = rows[0].risk_index
        latest = rows[-1].risk_index
        increase = latest - earliest

        if increase >= SPIKE_THRESHOLD:
            logger.warning(
                "Geopolitical spike detected for region %s: +%.1f points", region_id, increase
            )
            await publish(
                RISK_UPDATES_TOPIC,
                {
                    "event": "geopolitical_spike",
                    "region_id": str(region_id),
                    "increase": increase,
                    "current_index": latest,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            return True
        return False
