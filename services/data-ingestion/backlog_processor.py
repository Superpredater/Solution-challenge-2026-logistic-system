"""Backlog processor — replays buffered events in chronological order."""

from __future__ import annotations

import logging
from typing import Any

from services.shared.kafka import publish
from .normalizer import Normalizer
from .schema_validator import SchemaValidator
from .rest_poller import TOPIC_MAP

logger = logging.getLogger(__name__)


class BacklogProcessor:
    """Replays a list of buffered events in chronological order."""

    def __init__(self) -> None:
        self._normalizer = Normalizer()
        self._validator = SchemaValidator()

    async def process_backlog(
        self,
        events: list[dict[str, Any]],
        source_type: str,
    ) -> None:
        """
        Sort *events* by timestamp ascending and publish each to the
        appropriate Kafka topic.
        """
        sorted_events = sorted(
            events,
            key=lambda e: e.get("timestamp") or e.get("ts") or "",
        )

        for raw in sorted_events:
            event_type: str = raw.get("event_type", "carrier_update")
            normalized = self._normalizer.normalize(raw, source_type, event_type)
            try:
                event = await self._validator.validate(normalized, source_type)
            except Exception:
                continue  # DLQ already written

            topic = TOPIC_MAP.get(event_type, "raw.carrier.updates")
            await publish(topic, event.model_dump(mode="json"))
            logger.debug("Backlog: published %s → %s", event.event_id, topic)
