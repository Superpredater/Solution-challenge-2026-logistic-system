"""Decision audit REST API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.database import get_session
from services.shared.orm_models import DecisionAuditEntryORM

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])


def _require_manager_or_admin(role: str = "Admin") -> str:
    """Dependency stub — in production this reads from JWT claims."""
    if role not in ("Manager", "Admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return role


@router.get("/audit")
async def get_audit_entries(
    lookback_days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    result = await session.execute(
        select(DecisionAuditEntryORM)
        .where(DecisionAuditEntryORM.timestamp >= since)
        .order_by(DecisionAuditEntryORM.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    entries = result.scalars().all()
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "entry_id": str(e.entry_id),
                "tenant_id": str(e.tenant_id),
                "shipment_id": str(e.shipment_id),
                "decision_type": e.decision_type,
                "triggering_risk_score": e.triggering_risk_score,
                "actor": e.actor,
                "actor_role": e.actor_role,
                "previous_route_id": str(e.previous_route_id),
                "new_route_id": str(e.new_route_id),
                "timestamp": e.timestamp.isoformat(),
            }
            for e in entries
        ],
    }
