"""Main RiskEngine — wires all risk components together."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.kafka import publish
from services.shared.models import InternalEvent, RiskWeights
from services.shared.orm_models import RiskScoreEventORM, ShipmentORM
from .escalation_detector import EscalationDetector
from .evaluators import (
    GeopoliticalRiskEvaluator,
    OperationalRiskEvaluator,
    WarStateEvaluator,
    WeatherRiskEvaluator,
)
from .risk_aggregator import RiskAggregator

logger = logging.getLogger(__name__)

RISK_UPDATES_TOPIC = "risk.score.updates"
DISRUPTION_TOPIC = "disruption.detected"
DATA_UNAVAILABLE_MINIMUM_SCORE = 50.0

# Default weights (tenant-configurable in production)
DEFAULT_WEIGHTS = RiskWeights()


class RiskEngine:
    """Evaluates and persists risk scores for shipments affected by an event."""

    def __init__(self) -> None:
        self._weather_eval = WeatherRiskEvaluator()
        self._operational_eval = OperationalRiskEvaluator()
        self._war_eval = WarStateEvaluator()
        self._geo_eval = GeopoliticalRiskEvaluator()
        self._aggregator = RiskAggregator()
        self._escalation = EscalationDetector()

    async def process_event(self, event: InternalEvent, session: AsyncSession) -> None:
        """
        Evaluate all shipments affected by *event*, update risk scores,
        persist RiskScoreEvent rows, and publish to Kafka.
        """
        affected_shipments = await self._find_affected_shipments(event, session)

        for shipment in affected_shipments:
            try:
                score, components = await self._compute_score(shipment, event, session)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Data unavailable for shipment %s (%s); applying minimum score",
                    shipment.shipment_id, exc,
                )
                score = DATA_UNAVAILABLE_MINIMUM_SCORE
                components = {
                    "weather": 0.0,
                    "operational": 0.0,
                    "war_state": 0.0,
                    "geopolitical": 0.0,
                }

            await self._persist_score(shipment, score, components, session)
            await self._publish_score(shipment, score, event)
            await self._escalation.check_escalation(
                UUID(str(shipment.shipment_id)), score, session
            )

            if score >= 70:
                await publish(
                    DISRUPTION_TOPIC,
                    {
                        "event": "disruption_detected",
                        "shipment_id": str(shipment.shipment_id),
                        "tenant_id": str(shipment.tenant_id),
                        "risk_score": score,
                        "trigger_event_id": str(event.event_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _find_affected_shipments(
        self, event: InternalEvent, session: AsyncSession
    ) -> list:
        """Return shipments potentially affected by the event."""
        query = select(ShipmentORM).where(
            ShipmentORM.status.in_(["In_Transit", "Delayed"])
        )
        if event.node_ids:
            # Filter to shipments whose active route passes through affected nodes
            # (simplified: match by region for now)
            pass
        result = await session.execute(query)
        return result.scalars().all()

    async def _compute_score(
        self, shipment, event: InternalEvent, session: AsyncSession
    ) -> tuple[float, dict]:
        payload = event.payload

        weather_score = self._weather_eval.evaluate(
            payload if event.event_type == "weather_update" else {}
        )
        carrier_score = float(getattr(shipment, "carrier_risk_score", 0.0) or 0.0)
        dwell = float(getattr(shipment, "current_dwell_time_hours", 0.0) or 0.0)
        p90 = float(getattr(shipment, "p90_dwell_time_hours", 0.0) or 0.0)
        operational_score = self._operational_eval.evaluate(carrier_score, dwell, p90)

        war_state = getattr(shipment, "war_state", "Safe") or "Safe"
        war_score = self._war_eval.evaluate(war_state)

        geo_index = float(getattr(shipment, "geopolitical_risk_index", 0.0) or 0.0)
        geo_score = self._geo_eval.evaluate(geo_index)

        weights = DEFAULT_WEIGHTS
        total = self._aggregator.compute(
            weather_score, operational_score, war_score, geo_score, weights
        )
        return total, {
            "weather": weather_score,
            "operational": operational_score,
            "war_state": war_score,
            "geopolitical": geo_score,
        }

    async def _persist_score(
        self, shipment, score: float, components: dict, session: AsyncSession
    ) -> None:
        event_row = RiskScoreEventORM(
            event_id=uuid4(),
            shipment_id=shipment.shipment_id,
            tenant_id=shipment.tenant_id,
            risk_score=score,
            weather_component=components["weather"],
            operational_component=components["operational"],
            war_state_component=components["war_state"],
            geopolitical_component=components["geopolitical"],
            recorded_at=datetime.now(timezone.utc),
        )
        session.add(event_row)

        await session.execute(
            update(ShipmentORM)
            .where(ShipmentORM.shipment_id == shipment.shipment_id)
            .values(
                risk_score=score,
                risk_score_updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    async def _publish_score(self, shipment, score: float, event: InternalEvent) -> None:
        await publish(
            RISK_UPDATES_TOPIC,
            {
                "event": "risk_score_update",
                "shipment_id": str(shipment.shipment_id),
                "tenant_id": str(shipment.tenant_id),
                "risk_score": score,
                "trigger_event_id": str(event.event_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
