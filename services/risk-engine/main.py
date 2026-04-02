"""Risk Engine — Kafka consumer entry point with ScheduledRecalculator."""

from __future__ import annotations

import asyncio
import logging

from services.shared.database import get_db_session as get_session
from services.shared.kafka import consume
from services.shared.models import InternalEvent
from .risk_engine import RiskEngine
from .scheduled_recalculator import ScheduledRecalculator

logger = logging.getLogger(__name__)

TOPICS = [
    "raw.weather.events",
    "raw.carrier.updates",
    "raw.port.events",
    "geopolitical.risk.updates",
    "war.state.updates",
]

_engine = RiskEngine()


async def handle_message(topic: str, value: dict) -> None:
    try:
        event = InternalEvent.model_validate(value)
    except Exception as exc:
        logger.warning("Invalid event on %s: %s", topic, exc)
        return

    async with get_session() as session:
        await _engine.process_event(event, session)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Risk Engine starting...")

    recalculator = ScheduledRecalculator()
    asyncio.create_task(recalculator.start_background_task())

    await consume(TOPICS, group_id="risk-engine", handler=handle_message)


if __name__ == "__main__":
    asyncio.run(main())
