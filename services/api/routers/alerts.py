"""REST API — /api/v1/alerts router."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal
from services.shared.orm_models import AlertDeliveryORM, AlertORM

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_alerts(
    severity: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    principal=Depends(require_permission("alerts:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    q = select(AlertORM).where(AlertORM.tenant_id == UUID(tenant_id))
    if severity:
        q = q.where(AlertORM.severity == severity)
    q = q.order_by(AlertORM.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    rows = result.scalars().all()
    return {"page": page, "page_size": page_size, "items": [_alert_dict(r) for r in rows]}


@router.get("/{alert_id}")
async def get_alert(
    alert_id: UUID,
    principal=Depends(require_permission("alerts:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from fastapi import HTTPException

    _, tenant_id, _ = principal
    result = await session.execute(
        select(AlertORM).where(
            AlertORM.alert_id == alert_id,
            AlertORM.tenant_id == UUID(tenant_id),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_dict(row)


@router.get("/{alert_id}/deliveries")
async def get_alert_deliveries(
    alert_id: UUID,
    principal=Depends(require_permission("alerts:read")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(AlertDeliveryORM).where(
            AlertDeliveryORM.alert_id == alert_id,
            AlertDeliveryORM.tenant_id == UUID(tenant_id),
        )
    )
    rows = result.scalars().all()
    return [
        {
            "delivery_id": str(r.delivery_id),
            "alert_id": str(r.alert_id),
            "stakeholder_id": str(r.stakeholder_id),
            "channel": r.channel,
            "status": r.status,
            "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None,
            "retry_count": r.retry_count,
        }
        for r in rows
    ]


def _alert_dict(r: AlertORM) -> dict[str, Any]:
    return {
        "alert_id": str(r.alert_id),
        "tenant_id": str(r.tenant_id),
        "shipment_id": str(r.shipment_id) if r.shipment_id else None,
        "disruption_id": str(r.disruption_id) if r.disruption_id else None,
        "severity": r.severity,
        "trigger_type": r.trigger_type,
        "message": r.message,
        "ai_explanation": r.ai_explanation,
        "created_at": r.created_at.isoformat(),
    }
