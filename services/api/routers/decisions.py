"""REST API — /api/v1/decisions router (decision audit trail)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal
from services.shared.orm_models import DecisionAuditEntryORM

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/audit")
async def get_decision_audit(
    lookback_days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    principal=Depends(require_permission("audit:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from sqlalchemy import text
    from datetime import datetime, timezone, timedelta

    _, tenant_id, _ = principal
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    result = await session.execute(
        select(DecisionAuditEntryORM)
        .where(
            DecisionAuditEntryORM.tenant_id == UUID(tenant_id),
            DecisionAuditEntryORM.timestamp >= since,
        )
        .order_by(DecisionAuditEntryORM.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.scalars().all()
    return {
        "page": page,
        "page_size": page_size,
        "lookback_days": lookback_days,
        "items": [
            {
                "entry_id": str(r.entry_id),
                "shipment_id": str(r.shipment_id),
                "decision_type": r.decision_type,
                "triggering_risk_score": r.triggering_risk_score,
                "actor": r.actor,
                "actor_role": r.actor_role,
                "previous_route_id": str(r.previous_route_id),
                "new_route_id": str(r.new_route_id),
                "timestamp": r.timestamp.isoformat(),
            }
            for r in rows
        ],
    }
