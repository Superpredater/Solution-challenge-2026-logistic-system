"""REST API — /api/v1/disruptions router."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal
from services.shared.orm_models import DisruptionORM

router = APIRouter(prefix="/api/v1/disruptions", tags=["disruptions"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_disruptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    principal=Depends(require_permission("shipments:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(DisruptionORM)
        .where(
            DisruptionORM.tenant_id == UUID(tenant_id),
            DisruptionORM.resolved_at.is_(None),
        )
        .order_by(DisruptionORM.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.scalars().all()
    return {
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "disruption_id": str(r.disruption_id),
                "disruption_type": r.disruption_type,
                "severity": r.severity,
                "description": r.description,
                "affected_node_ids": r.affected_node_ids,
                "started_at": r.started_at.isoformat(),
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }
