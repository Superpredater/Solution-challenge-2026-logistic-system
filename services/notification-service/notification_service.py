"""Notification service wiring all delivery components."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.models import Alert, AlertDelivery, Stakeholder, Tenant
from .alert_classifier import AlertClassifier
from .deduplication_filter import DeduplicationFilter
from .delivery_audit_logger import DeliveryAuditLogger
from .quiet_period_enforcer import QuietPeriodEnforcer
from .senders import EmailSender, SMSSender, WebhookDispatcher

logger = logging.getLogger(__name__)


class NotificationService:
    """Orchestrate alert delivery across all channels."""

    def __init__(
        self,
        email_sender: EmailSender,
        sms_sender: SMSSender,
        webhook_dispatcher: WebhookDispatcher,
        dedup_filter: DeduplicationFilter,
        audit_logger: DeliveryAuditLogger,
    ) -> None:
        self._email = email_sender
        self._sms = sms_sender
        self._webhook = webhook_dispatcher
        self._dedup = dedup_filter
        self._audit = audit_logger
        self._classifier = AlertClassifier()
        self._quiet = QuietPeriodEnforcer()

    async def deliver_alert(
        self,
        alert: Alert,
        stakeholders: list[Stakeholder],
        tenant: Tenant,
        session: AsyncSession,
    ) -> None:
        severity = self._classifier.classify(alert.risk_score if hasattr(alert, "risk_score") else 0.0, alert.trigger_type)

        if self._quiet.should_suppress(tenant, severity):
            logger.info("Alert %s suppressed (quiet period)", alert.alert_id)
            return

        for stakeholder in stakeholders:
            disruption_id = alert.disruption_id or uuid.UUID(int=0)
            shipment_id = alert.shipment_id or uuid.UUID(int=0)

            if await self._dedup.is_duplicate(disruption_id, shipment_id, stakeholder.stakeholder_id):
                logger.debug("Duplicate alert suppressed for stakeholder %s", stakeholder.stakeholder_id)
                continue

            for channel in stakeholder.notification_channels:
                success = await self._dispatch(channel, stakeholder, alert)
                delivery = AlertDelivery(
                    delivery_id=uuid.uuid4(),
                    alert_id=alert.alert_id,
                    stakeholder_id=stakeholder.stakeholder_id,
                    channel=channel,
                    status="delivered" if success else "failed",
                    delivered_at=datetime.now(timezone.utc) if success else None,
                    retry_count=0,
                )
                await self._audit.log(delivery, session)

            await self._dedup.mark_sent(disruption_id, shipment_id, stakeholder.stakeholder_id)

    async def _dispatch(self, channel: str, stakeholder: Stakeholder, alert: Alert) -> bool:
        if channel == "email" and stakeholder.email:
            return await self._email.send(stakeholder.email, f"Alert: {alert.severity}", alert.message)
        if channel == "sms" and stakeholder.phone:
            return await self._sms.send(stakeholder.phone, alert.message)
        if channel == "webhook" and stakeholder.webhook_url:
            return await self._webhook.send(
                stakeholder.webhook_url,
                alert.model_dump(mode="json"),
                secret="",
            )
        return False
