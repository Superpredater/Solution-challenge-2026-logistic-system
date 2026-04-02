"""REST API — /api/v1/regions router."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal
from services.shared.orm_models import GeopoliticalRegionORM

router = APIRouter(prefix="/api/v1/regions", tags=["regions"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/{region_id}/risk")
async def get_region_risk(
    region_id: UUID,
    principal=Depends(require_permission("regions:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(GeopoliticalRegionORM).where(
            GeopoliticalRegionORM.region_id == region_id,
            GeopoliticalRegionORM.tenant_id == UUID(tenant_id),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Region not found")
    return {
        "region_id": str(row.region_id),
        "name": row.name,
        "geopolitical_risk_index": row.geopolitical_risk_index,
        "war_state": row.war_state,
        "risk_index_updated_at": row.risk_index_updated_at.isoformat(),
        "war_state_updated_at": row.war_state_updated_at.isoformat(),
    }
