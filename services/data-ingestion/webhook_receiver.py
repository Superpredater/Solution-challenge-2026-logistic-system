"""FastAPI webhook receiver for carrier and port push events."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from services.shared.kafka import publish
from .normalizer import Normalizer
from .schema_validator import SchemaValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

_normalizer = Normalizer()
_validator = SchemaValidator()


async def _ingest(raw: dict[str, Any], source_type: str, event_type: str, topic: str) -> dict:
    normalized = _normalizer.normalize(raw, source_type, event_type)
    try:
        event = await _validator.validate(normalized, source_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await publish(topic, event.model_dump(mode="json"))
    return {"status": "accepted", "event_id": str(event.event_id)}


@router.post("/carrier")
async def carrier_webhook(payload: dict[str, Any]) -> dict:
    """Accept carrier push events and publish to raw.carrier.updates."""
    return await _ingest(payload, "webhook", "carrier_update", "raw.carrier.updates")


@router.post("/port")
async def port_webhook(payload: dict[str, Any]) -> dict:
    """Accept port authority push events and publish to raw.port.events."""
    return await _ingest(payload, "webhook", "port_event", "raw.port.events")
