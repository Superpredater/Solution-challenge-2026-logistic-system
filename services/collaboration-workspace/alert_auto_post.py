"""Collaboration Workspace — AlertAutoPost: auto-posts disruption alerts to channels."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.models import Alert, CollaborationMessage
from .message_channel import MessageChannel

logger = logging.getLogger(__name__)

SYSTEM_AUTHOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class AlertAutoPost:
    """Subscribes to disruption.detected and posts system messages (Req 17.5)."""

    def __init__(self) -> None:
        self._channel = MessageChannel()

    async def post_disruption_alert(
        self,
        shipment_id: UUID,
        alert: Alert,
        tenant_id: UUID,
        session: AsyncSession,
    ) -> CollaborationMessage:
        """Create a system message summarizing the disruption in the shipment channel."""
        content = self._format_alert(alert)
        message = await self._channel.post_message(
            shipment_id=shipment_id,
            author_id=SYSTEM_AUTHOR_ID,
            content=content,
            tenant_id=tenant_id,
            session=session,
        )
        logger.info(
            "Auto-posted disruption alert %s to shipment %s channel",
            alert.alert_id,
            shipment_id,
        )
        return message

    def _format_alert(self, alert: Alert) -> str:
        lines = [
            f"🚨 **Disruption Alert** [{alert.severity}]",
            f"Type: {alert.trigger_type}",
            f"Message: {alert.message}",
        ]
        if alert.ai_explanation:
            lines.append(f"AI Analysis: {alert.ai_explanation}")
        lines.append(f"Detected at: {alert.created_at.isoformat()}")
        return "\n".join(lines)
