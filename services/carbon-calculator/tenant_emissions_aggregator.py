"""Aggregate carbon emissions per tenant over a time range."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.orm_models import ShipmentORM


class TenantEmissionsAggregator:
    """Sum carbon_kg for a tenant's shipments within a time window."""

    async def aggregate(
        self,
        tenant_id: UUID,
        start: datetime,
        end: datetime,
        session: AsyncSession,
    ) -> float:
        """Return total kg CO₂ for the tenant in [start, end]."""
        result = await session.execute(
            select(func.coalesce(func.sum(ShipmentORM.carbon_kg), 0.0)).where(
                ShipmentORM.tenant_id == tenant_id,
                ShipmentORM.created_at >= start,
                ShipmentORM.created_at <= end,
            )
        )
        return float(result.scalar_one())
