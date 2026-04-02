"""Geopolitical Engine — entry point."""

from __future__ import annotations

import asyncio
import logging

from .news_ingestion_consumer import NewsIngestionConsumer

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Geopolitical Engine starting...")
    consumer = NewsIngestionConsumer()
    await consumer.start()


if __name__ == "__main__":
    asyncio.run(main())
