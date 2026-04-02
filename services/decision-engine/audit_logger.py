"""Audit logger for autonomous decisions and manual overrides."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.models import DecisionAuditEntry
from services.shared.orm_models import DecisionAuditEntryORM

logger = logging.getLogger(__name__)


class AuditLogger:
    """Persist decision audit entries to the database."""

    async def log_decision(
        self,
        entry: DecisionAuditEntry,
        session: AsyncSession,
    ) -> None:
        orm = DecisionAuditEntryORM(
            entry_id=entry.entry_id,
            tenant_id=entry.tenant_id,
            shipment_id=entry.shipment_id,
            decision_type=entry.decision_type,
            triggering_risk_score=entry.triggering_risk_score,
            recommendation_id=entry.recommendation_id,
            actor=entry.actor,
            actor_role=entry.actor_role,
            previous_route_id=entry.previous_route_id,
            new_route_id=entry.new_route_id,
            timestamp=entry.timestamp,
        )
        session.add(orm)
        await session.commit()
        logger.debug("Audit entry %s persisted", entry.entry_id)

    async def log_override(
        self,
        entry: DecisionAuditEntry,
        session: AsyncSession,
    ) -> None:
        await self.log_decision(entry, session)
