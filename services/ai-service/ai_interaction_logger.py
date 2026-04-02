"""Persist AI interaction logs to the database."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.models import AIInteractionLog
from services.shared.orm_models import AIInteractionLogORM

logger = logging.getLogger(__name__)


class AIInteractionLogger:
    """Write AIInteractionLog records to ai_interaction_logs table."""

    async def log(self, interaction: AIInteractionLog, session: AsyncSession) -> None:
        orm = AIInteractionLogORM(
            interaction_id=interaction.interaction_id,
            tenant_id=interaction.tenant_id,
            stakeholder_id=interaction.stakeholder_id,
            interaction_type=interaction.interaction_type,
            query=interaction.query,
            response=interaction.response,
            model_used=interaction.model_used,
            latency_ms=interaction.latency_ms,
            fallback_used=interaction.fallback_used,
            timestamp=interaction.timestamp,
        )
        session.add(orm)
        await session.commit()
        logger.debug("AI interaction %s logged", interaction.interaction_id)
