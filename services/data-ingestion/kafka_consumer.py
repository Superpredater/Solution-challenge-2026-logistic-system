"""External Kafka consumer — normalizes and republishes to internal topics."""

from __future__ import annotations

import logging
from typing import Any

from services.shared.kafka import consume, publish
from .normalizer import Normalizer
from .schema_validator import SchemaValidator
from .rest_poller import TOPIC_MAP

logger = logging.getLogger(__name__)


class ExternalKafkaConsumer:
    """
    Subscribes to external Kafka topics, normalizes each message, validates it,
    and republishes to the appropriate internal topic.
    """

    def __init__(
        self,
        topics: list[str],
        source_type: str = "kafka",
        event_type: str = "carrier_update",
        group_id: str = "data-ingestion-external",
    ) -> None:
        self._topics = topics
        self._source_type = source_type
        self._event_type = event_type
        self._group_id = group_id
        self._normalizer = Normalizer()
        self._validator = SchemaValidator()

    async def start(self) -> None:
        """Start consuming; runs until cancelled."""
        await consume(self._topics, group_id=self._group_id, handler=self._handle)

    async def _handle(self, topic: str, value: dict[str, Any]) -> None:
        normalized = self._normalizer.normalize(value, self._source_type, self._event_type)
        try:
            event = await self._validator.validate(normalized, self._source_type)
        except Exception:
            return  # DLQ already written by validator

        internal_topic = TOPIC_MAP.get(self._event_type, "raw.carrier.updates")
        await publish(internal_topic, event.model_dump(mode="json"))
        logger.debug("Republished %s → %s", event.event_id, internal_topic)
