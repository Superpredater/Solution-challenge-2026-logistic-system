"""REST API — /api/v1/edge router (edge agent sync and heartbeat)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.database import AsyncSessionLocal
from services.shared.kafka import publish

router = APIRouter(prefix="/api/v1/edge", tags=["edge"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/sync", status_code=status.HTTP_200_OK)
async def edge_sync(
    body: dict[str, Any],
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Accept batched edge agent events and publish to Kafka."""
    events: list[dict[str, Any]] = body.get("events", [])
    published = 0
    for event in events:
        try:
            await publish(
                topic="raw.shipment.positions",
                value={**event.get("event", {}), "source_type": "edge"},
                key=event.get("event", {}).get("shipment_id"),
            )
            published += 1
        except Exception:
            pass
    return {"received": len(events), "published": published}


@router.post("/heartbeat", status_code=status.HTTP_200_OK)
async def edge_heartbeat(
    body: dict[str, Any],
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Record edge agent heartbeat."""
    agent_id = body.get("agent_id", "")
    timestamp = body.get("timestamp", datetime.now(timezone.utc).isoformat())
    # In production: update EdgeAgentORM.last_heartbeat_at
    return {"agent_id": agent_id, "acknowledged_at": timestamp}
