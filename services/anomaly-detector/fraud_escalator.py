"""Escalate fraud/theft detections to Kafka and the database."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.kafka import publish
from services.shared.models import Shipment

logger = logging.getLogger(__name__)

TOPIC = "anomaly.detected"


class FraudEscalator:
    """Log shipment state snapshot and publish a High_Priority anomaly alert."""

    async def escalate(
        self,
        shipment: Shipment,
        patterns: list[str],
        session: AsyncSession,
    ) -> None:
        payload = {
            "event": "fraud_escalation",
            "alert_id": str(uuid.uuid4()),
            "shipment_id": str(shipment.shipment_id),
            "tenant_id": str(shipment.tenant_id),
            "patterns": patterns,
            "priority": "High",
            "shipment_snapshot": shipment.model_dump(mode="json"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await publish(TOPIC, payload, key=str(shipment.shipment_id))
        logger.warning(
            "Fraud escalation published for shipment %s — patterns: %s",
            shipment.shipment_id,
            patterns,
        )
