"""Redis-backed deduplication filter for alerts."""

from __future__ import annotations

from uuid import UUID

import redis.asyncio as aioredis

_TTL_SECONDS = 1800  # 30 minutes


class DeduplicationFilter:
    """Prevent duplicate alerts using Redis keys with 30-minute TTL."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    def _key(
        self,
        disruption_id: UUID,
        shipment_id: UUID,
        stakeholder_id: UUID,
    ) -> str:
        return f"dedup:{disruption_id}:{shipment_id}:{stakeholder_id}"

    async def is_duplicate(
        self,
        disruption_id: UUID,
        shipment_id: UUID,
        stakeholder_id: UUID,
    ) -> bool:
        key = self._key(disruption_id, shipment_id, stakeholder_id)
        return bool(await self._redis.exists(key))

    async def mark_sent(
        self,
        disruption_id: UUID,
        shipment_id: UUID,
        stakeholder_id: UUID,
    ) -> None:
        key = self._key(disruption_id, shipment_id, stakeholder_id)
        await self._redis.set(key, "1", ex=_TTL_SECONDS)
