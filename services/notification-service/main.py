"""Notification Service — Kafka consumer."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI

from services.shared.kafka import consume

logger = logging.getLogger(__name__)

app = FastAPI(title="Notification Service", version="1.0.0")

_TOPICS = [
    "disruption.detected",
    "risk.escalations",
    "war.state.updates",
    "anomaly.detected",
]


async def _handle_message(topic: str, value: dict[str, Any]) -> None:
    logger.info("Notification trigger from %s: %s", topic, value.get("event", topic))
    # In production: load alert, stakeholders, tenant; call NotificationService.deliver_alert


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(consume(_TOPICS, "notification-service", _handle_message))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
