"""Carrier Risk Profiler — background flag-check loop."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from services.shared.database import get_db_session as get_session
from services.shared.orm_models import CarrierProfileORM
from .high_risk_flag_detector import HighRiskFlagDetector

logger = logging.getLogger(__name__)

FLAG_CHECK_INTERVAL_SECONDS = 3600  # 1 hour


async def run_flag_checks() -> None:
    """Check all carriers for high-risk status every hour."""
    detector = HighRiskFlagDetector()
    while True:
        try:
            async with get_session() as session:
                result = await session.execute(select(CarrierProfileORM))
                carriers = result.scalars().all()
                logger.info("Running high-risk flag checks for %d carriers", len(carriers))
                for carrier in carriers:
                    await detector.check_and_flag(carrier.carrier_id, session)
                    await detector.clear_flag_if_recovered(carrier.carrier_id, session)
        except Exception as exc:  # noqa: BLE001
            logger.error("Flag check error: %s", exc)
        await asyncio.sleep(FLAG_CHECK_INTERVAL_SECONDS)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Carrier Risk Profiler starting...")
    await run_flag_checks()


if __name__ == "__main__":
    asyncio.run(main())
