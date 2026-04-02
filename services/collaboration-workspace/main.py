"""Collaboration Workspace — FastAPI service entry point."""

from __future__ import annotations

import asyncio
import logging

import uvicorn
from fastapi import FastAPI

from services.shared.kafka import consume
from services.shared.database import AsyncSessionLocal
from services.shared.models import Alert

from .websocket_handler import router as ws_router
from .alert_auto_post import AlertAutoPost

logger = logging.getLogger(__name__)

app = FastAPI(title="Collaboration Workspace", version="1.0.0")
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "collaboration-workspace"}


async def _handle_disruption(topic: str, event: dict) -> None:
    """Kafka consumer handler: post disruption alerts to collaboration channels."""
    try:
        shipment_id = event.get("shipment_id")
        tenant_id = event.get("tenant_id")
        if not shipment_id or not tenant_id:
            return

        from uuid import UUID
        from datetime import datetime, timezone

        alert = Alert(
            alert_id=event.get("alert_id", "00000000-0000-0000-0000-000000000000"),
            tenant_id=tenant_id,
            shipment_id=shipment_id,
            severity=event.get("severity", "Warning"),
            trigger_type=event.get("trigger_type", "risk_score_threshold"),
            message=event.get("message", "Disruption detected"),
            ai_explanation=event.get("ai_explanation"),
            created_at=datetime.now(timezone.utc),
        )

        poster = AlertAutoPost()
        async with AsyncSessionLocal() as session:
            await poster.post_disruption_alert(
                shipment_id=UUID(shipment_id),
                alert=alert,
                tenant_id=UUID(tenant_id),
                session=session,
            )
    except Exception as exc:
        logger.error("Failed to handle disruption event: %s", exc)


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(
        consume(
            topics=["disruption.detected"],
            group_id="collaboration-workspace",
            handler=_handle_disruption,
        )
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8010)
