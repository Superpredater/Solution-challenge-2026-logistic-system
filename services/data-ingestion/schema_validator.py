"""Schema validation for incoming events — writes failures to ingestion.dlq."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from services.shared.kafka import publish
from services.shared.models import InternalEvent

logger = logging.getLogger(__name__)

DLQ_TOPIC = "ingestion.dlq"


class SchemaValidator:
    """Validates raw dicts against the InternalEvent schema using Pydantic v2."""

    async def validate(self, raw: dict[str, Any], source_type: str) -> InternalEvent:
        """
        Validate *raw* against InternalEvent.

        On failure: writes a structured error record to ``ingestion.dlq`` and
        re-raises the ``ValidationError``.
        """
        try:
            return InternalEvent.model_validate(raw)
        except ValidationError as exc:
            await self._send_to_dlq(raw, source_type, exc)
            raise

    async def _send_to_dlq(
        self,
        raw: dict[str, Any],
        source_type: str,
        exc: ValidationError,
    ) -> None:
        dlq_record = {
            "raw_payload": raw,
            "error_details": exc.errors(include_url=False),
            "source_type": source_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await publish(DLQ_TOPIC, dlq_record)
        except Exception as kafka_exc:  # noqa: BLE001
            logger.error("Failed to write to DLQ: %s", kafka_exc)
