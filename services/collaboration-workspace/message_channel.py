"""Collaboration Workspace — MessageChannel: per-shipment threaded messaging."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.config import settings
from services.shared.models import CollaborationMessage
from services.shared.orm_models import CollaborationMessageORM

logger = logging.getLogger(__name__)


def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


class MessageChannel:
    """Per-shipment threaded message channel with WebSocket delivery (Req 17.2)."""

    async def post_message(
        self,
        shipment_id: UUID,
        author_id: UUID,
        content: str,
        tenant_id: UUID,
        session: AsyncSession,
    ) -> CollaborationMessage:
        """Persist a message and publish to Redis pub/sub."""
        now = datetime.now(timezone.utc)
        message_id = uuid.uuid4()

        orm = CollaborationMessageORM(
            message_id=message_id,
            tenant_id=tenant_id,
            shipment_id=shipment_id,
            author_id=author_id,
            content=content,
            created_at=now,
        )
        session.add(orm)
        await session.commit()

        message = CollaborationMessage(
            message_id=message_id,
            tenant_id=tenant_id,
            shipment_id=shipment_id,
            author_id=author_id,
            content=content,
            created_at=now,
        )
        await self.publish_to_websocket(message)
        return message

    async def get_messages(
        self,
        shipment_id: UUID,
        tenant_id: UUID,
        session: AsyncSession,
        limit: int = 50,
    ) -> list[CollaborationMessage]:
        """Retrieve the most recent messages for a shipment."""
        result = await session.execute(
            select(CollaborationMessageORM)
            .where(
                CollaborationMessageORM.shipment_id == shipment_id,
                CollaborationMessageORM.tenant_id == tenant_id,
            )
            .order_by(CollaborationMessageORM.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            CollaborationMessage(
                message_id=r.message_id,
                tenant_id=r.tenant_id,
                shipment_id=r.shipment_id,
                author_id=r.author_id,
                content=r.content,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in reversed(rows)
        ]

    async def publish_to_websocket(self, message: CollaborationMessage) -> None:
        """Publish message to Redis pub/sub channel collab:{shipment_id}."""
        channel = f"collab:{message.shipment_id}"
        payload = json.dumps(
            {
                "message_id": str(message.message_id),
                "author_id": str(message.author_id),
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
        )
        try:
            redis = _get_redis()
            await redis.publish(channel, payload)
            await redis.aclose()
        except Exception as exc:
            logger.warning("Failed to publish to Redis channel %s: %s", channel, exc)
