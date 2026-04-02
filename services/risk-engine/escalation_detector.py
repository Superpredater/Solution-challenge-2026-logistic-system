"""Detects risk score escalations (≥20 point increase in 1 hour)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.kafka import publish
from services.shared.orm_models import RiskScoreEventORM

logger = logging.getLogger(__name__)

ESCALATION_TOPIC = "risk.escalations"
ESCALATION_THRESHOLD = 20.0
WINDOW_HOURS = 1


class EscalationDetector:
    """Detects when a shipment's risk score increases ≥ 20 points within 1 hour."""

    async def check_escalation(
        self,
        shipment_id: UUID,
        current_score: float,
        session: AsyncSession,
    ) -> bool:
        """
        Returns True if an escalation is detected and publishes to risk.escalations.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
        result = await session.execute(
            select(RiskScoreEventORM)
            .where(
                RiskScoreEventORM.shipment_id == shipment_id,
                RiskScoreEventORM.recorded_at >= cutoff,
            )
            .order_by(RiskScoreEventORM.recorded_at.asc())
        )
        rows = result.scalars().all()
        if not rows:
            return False

        min_score = min(r.risk_score for r in rows)
        increase = current_score - min_score

        if increase >= ESCALATION_THRESHOLD:
            logger.warning(
                "Escalation detected for shipment %s: +%.1f points", shipment_id, increase
            )
            await publish(
                ESCALATION_TOPIC,
                {
                    "event": "risk_escalation",
                    "shipment_id": str(shipment_id),
                    "current_score": current_score,
                    "increase": increase,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            return True
        return False
