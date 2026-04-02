"""REST API — /api/v1/carbon router."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal
from services.shared.orm_models import ShipmentORM

router = APIRouter(prefix="/api/v1/carbon", tags=["carbon"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/summary")
async def carbon_summary(
    principal=Depends(require_permission("shipments:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(func.sum(ShipmentORM.carbon_kg), func.count(ShipmentORM.shipment_id)).where(
            ShipmentORM.tenant_id == UUID(tenant_id)
        )
    )
    row = result.one()
    return {
        "tenant_id": tenant_id,
        "total_carbon_kg": round(row[0] or 0.0, 2),
        "shipment_count": row[1] or 0,
    }
