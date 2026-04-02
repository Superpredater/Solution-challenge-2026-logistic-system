"""Scheduled REST poller — polls external APIs and publishes to Kafka."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from services.shared.kafka import publish
from .normalizer import Normalizer
from .schema_validator import SchemaValidator

logger = logging.getLogger(__name__)

# Map event_type → Kafka topic
TOPIC_MAP: dict[str, str] = {
    "weather_update": "raw.weather.events",
    "carrier_update": "raw.carrier.updates",
    "port_event": "raw.port.events",
    "news_event": "raw.news.events",
    "shipment_position": "raw.shipment.positions",
    "edge_sync": "raw.shipment.positions",
}


class RestPoller:
    """Polls a list of REST sources on configurable intervals."""

    def __init__(self, sources: list[dict[str, Any]]) -> None:
        """
        Parameters
        ----------
        sources:
            Each entry must contain:
            - url: str
            - source_type: str  (e.g. "rest")
            - event_type: str   (e.g. "weather_update")
            - interval_seconds: int
            - headers: dict[str, str]  (optional)
        """
        self._sources = sources
        self._normalizer = Normalizer()
        self._validator = SchemaValidator()

    async def start(self) -> None:
        """Run all pollers concurrently; runs until cancelled."""
        tasks = [asyncio.create_task(self._poll_source(src)) for src in self._sources]
        await asyncio.gather(*tasks)

    async def _poll_source(self, source: dict[str, Any]) -> None:
        url: str = source["url"]
        source_type: str = source.get("source_type", "rest")
        event_type: str = source["event_type"]
        interval: int = int(source.get("interval_seconds", 60))
        headers: dict[str, str] = source.get("headers", {})

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    raw: Any = response.json()

                    # API may return a list or a single object
                    records = raw if isinstance(raw, list) else [raw]

                    for record in records:
                        await self._process_record(record, source_type, event_type)

                except httpx.HTTPError as exc:
                    logger.warning("HTTP error polling %s: %s", url, exc)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Unexpected error polling %s: %s", url, exc)

                await asyncio.sleep(interval)

    async def _process_record(
        self,
        raw: dict[str, Any],
        source_type: str,
        event_type: str,
    ) -> None:
        normalized = self._normalizer.normalize(raw, source_type, event_type)
        try:
            event = await self._validator.validate(normalized, source_type)
        except Exception:
            # Validation failure already written to DLQ; skip this record
            return

        topic = TOPIC_MAP.get(event_type, "raw.carrier.updates")
        await publish(topic, event.model_dump(mode="json"))
        logger.debug("Published %s to %s", event.event_id, topic)
