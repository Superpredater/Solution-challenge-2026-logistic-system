"""Region registry — CRUD helpers for GeopoliticalRegion records."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.models import GeopoliticalRegion
from services.shared.orm_models import GeopoliticalRegionORM

logger = logging.getLogger(__name__)


class RegionRegistry:
    """Provides async access to GeopoliticalRegion persistence."""

    async def get_region(self, region_id: UUID, session: AsyncSession) -> GeopoliticalRegion:
        result = await session.execute(
            select(GeopoliticalRegionORM).where(GeopoliticalRegionORM.region_id == region_id)
        )
        row = result.scalar_one()
        return GeopoliticalRegion.model_validate(row.__dict__)

    async def get_region_by_iso(
        self, iso_code: str, session: AsyncSession
    ) -> GeopoliticalRegion | None:
        result = await session.execute(
            select(GeopoliticalRegionORM).where(
                GeopoliticalRegionORM.iso_codes.contains([iso_code])
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return GeopoliticalRegion.model_validate(row.__dict__)

    async def update_risk_index(
        self, region_id: UUID, new_index: float, session: AsyncSession
    ) -> None:
        await session.execute(
            update(GeopoliticalRegionORM)
            .where(GeopoliticalRegionORM.region_id == region_id)
            .values(
                geopolitical_risk_index=new_index,
                risk_index_updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
        logger.info("Region %s risk index updated to %.1f", region_id, new_index)

    async def update_war_state(
        self, region_id: UUID, new_state: str, session: AsyncSession
    ) -> None:
        await session.execute(
            update(GeopoliticalRegionORM)
            .where(GeopoliticalRegionORM.region_id == region_id)
            .values(
                war_state=new_state,
                war_state_updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
        logger.info("Region %s war state updated to %s", region_id, new_state)
