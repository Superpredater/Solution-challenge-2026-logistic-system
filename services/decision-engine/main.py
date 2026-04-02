"""Decision Engine — Kafka consumer for routing.recommendations."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI

from services.shared.kafka import consume
from services.shared.models import RerouteRecommendation
from .decision_audit_api import router as audit_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Decision Engine", version="1.0.0")
app.include_router(audit_router)


async def _handle_message(topic: str, value: dict[str, Any]) -> None:
    if topic == "routing.recommendations":
        event = value.get("event")
        if event == "no_route_available":
            logger.warning(
                "No route available for shipment %s", value.get("shipment_id")
            )
            return
        try:
            rec = RerouteRecommendation.model_validate(value)
        except Exception as exc:
            logger.error("Invalid recommendation payload: %s", exc)
            return
        logger.info(
            "Received recommendation %s for shipment %s (risk=%.1f)",
            rec.recommendation_id,
            rec.shipment_id,
            rec.triggering_risk_score,
        )
        # In production: load tenant, call AutonomousExecutor, log via AuditLogger


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(
        consume(["routing.recommendations"], "decision-engine", _handle_message)
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
