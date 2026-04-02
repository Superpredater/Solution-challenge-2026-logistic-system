"""Kafka consumer for raw.news.events — routes through NLP → index update → war state."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.database import get_db_session as get_session
from services.shared.kafka import consume
from .geopolitical_index_updater import GeopoliticalIndexUpdater
from .nlp_signal_extractor import NLPSignalExtractor
from .war_state_classifier import WarStateClassifier
from .region_registry import RegionRegistry

logger = logging.getLogger(__name__)

TOPIC = "raw.news.events"
GROUP_ID = "geopolitical-engine"


class NewsIngestionConsumer:
    """Processes news events end-to-end through the geopolitical pipeline."""

    def __init__(self) -> None:
        self._extractor = NLPSignalExtractor()
        self._updater = GeopoliticalIndexUpdater()
        self._classifier = WarStateClassifier()
        self._registry = RegionRegistry()

    async def start(self) -> None:
        await consume([TOPIC], group_id=GROUP_ID, handler=self._handle)

    async def _handle(self, topic: str, value: dict[str, Any]) -> None:
        payload: dict = value.get("payload", value)
        text: str = payload.get("body") or payload.get("title") or ""
        language: str = payload.get("language", "en")
        region_id_raw = value.get("region_id")

        if not text:
            logger.debug("Skipping news event with empty text")
            return

        signal = self._extractor.extract(text, language)
        signal_dict = signal.model_dump()

        if region_id_raw is None:
            logger.debug("News event has no region_id; skipping index update")
            return

        region_id = UUID(str(region_id_raw))

        async with get_session() as session:
            await self._updater.update(region_id, signal_dict, session)
            await self._updater.check_spike(region_id, session)

            region = await self._registry.get_region(region_id, session)
            new_state = self._classifier.classify(signal_dict, region.war_state)
            if new_state != region.war_state:
                await self._classifier.update_region_war_state(region_id, new_state, session)
