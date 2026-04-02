"""Anomaly Detector — Kafka consumer for raw.shipment.positions."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI

from services.shared.kafka import consume
from .behavioral_pattern_analyzer import BehavioralPatternAnalyzer
from .route_deviation_monitor import RouteDeviationMonitor

logger = logging.getLogger(__name__)

app = FastAPI(title="Anomaly Detector", version="1.0.0")

_deviation_monitor = RouteDeviationMonitor()
_pattern_analyzer = BehavioralPatternAnalyzer()


async def _handle_message(topic: str, value: dict[str, Any]) -> None:
    if topic != "raw.shipment.positions":
        return

    lat = value.get("latitude", 0.0)
    lon = value.get("longitude", 0.0)
    waypoints = value.get("planned_waypoints", [])
    shipment_id = value.get("shipment_id")

    if _deviation_monitor.check_deviation(lat, lon, waypoints):
        logger.warning("Route deviation detected for shipment %s", shipment_id)
        # In production: load shipment, call FraudEscalator

    events = value.get("recent_events", [])
    if shipment_id and events:
        from uuid import UUID
        result = _pattern_analyzer.analyze(UUID(shipment_id), events)
        if result["is_suspicious"]:
            logger.warning(
                "Suspicious patterns for shipment %s: %s",
                shipment_id,
                result["patterns"],
            )
            # In production: load shipment, call FraudEscalator


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(
        consume(["raw.shipment.positions"], "anomaly-detector", _handle_message)
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
