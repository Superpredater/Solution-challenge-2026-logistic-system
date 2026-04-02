"""Routing Engine — Kafka consumer for risk.score.updates."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import FastAPI

from services.shared.kafka import consume
from .route_graph import RouteGraph

logger = logging.getLogger(__name__)

app = FastAPI(title="Routing Engine", version="1.0.0")

# Shared in-memory graph (populated from Kafka events in production)
_graph = RouteGraph()


async def _handle_message(topic: str, value: dict[str, Any]) -> None:
    if topic == "risk.score.updates":
        risk_score = value.get("risk_score", 0.0)
        if risk_score > 70:
            logger.info(
                "High risk score %.1f for shipment %s — recommendation generation triggered",
                risk_score,
                value.get("shipment_id"),
            )
            # In production: load shipment from DB, call RecommendationPublisher
    elif topic == "war.state.updates":
        node_ids = [UUID(n) for n in value.get("node_ids", [])]
        _graph.update_from_war_state(
            UUID(value["region_id"]),
            value.get("war_state", "Safe"),
            node_ids,
        )
    elif topic == "disruption.detected":
        node_ids = [UUID(n) for n in value.get("affected_node_ids", [])]
        _graph.update_from_disruption(node_ids)


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(
        consume(
            ["risk.score.updates", "war.state.updates", "disruption.detected"],
            "routing-engine",
            _handle_message,
        )
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
