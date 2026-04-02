"""REST API — /api/v1/carriers router."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal
from services.shared.orm_models import CarrierProfileORM, RiskScoreEventORM

router = APIRouter(prefix="/api/v1/carriers", tags=["carriers"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_carriers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    principal=Depends(require_permission("carriers:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(CarrierProfileORM)
        .where(CarrierProfileORM.tenant_id == UUID(tenant_id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.scalars().all()
    return {"page": page, "page_size": page_size, "items": [_carrier_dict(r) for r in rows]}


@router.get("/{carrier_id}/profile")
async def get_carrier_profile(
    carrier_id: UUID,
    principal=Depends(require_permission("carriers:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(CarrierProfileORM).where(
            CarrierProfileORM.carrier_id == carrier_id,
            CarrierProfileORM.tenant_id == UUID(tenant_id),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Carrier not found")
    return _carrier_dict(row)


@router.get("/{carrier_id}/risk-history")
async def get_carrier_risk_history(
    carrier_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    principal=Depends(require_permission("carriers:read")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    # Carrier risk history is stored in risk_score_events aggregated by carrier
    # Return carrier profile history from carrier_deliveries
    from services.shared.orm_models import CarrierDeliveryORM

    result = await session.execute(
        select(CarrierDeliveryORM)
        .where(CarrierDeliveryORM.carrier_id == carrier_id)
        .order_by(CarrierDeliveryORM.recorded_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "carrier_id": str(carrier_id),
            "on_time": r.on_time,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in rows
    ]


def _carrier_dict(r: CarrierProfileORM) -> dict[str, Any]:
    return {
        "carrier_id": str(r.carrier_id),
        "name": r.name,
        "on_time_rate_90d": r.on_time_rate_90d,
        "on_time_rate_30d": r.on_time_rate_30d,
        "incident_count_90d": r.incident_count_90d,
        "capacity_reliability_score": r.capacity_reliability_score,
        "risk_score": r.risk_score,
        "is_high_risk": r.is_high_risk,
        "profile_updated_at": r.profile_updated_at.isoformat(),
    }
