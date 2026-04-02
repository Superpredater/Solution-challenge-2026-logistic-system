"""API Gateway — RateLimiterMiddleware: Redis token bucket per tenant/API key."""

from __future__ import annotations

import json
import math
import time
import uuid
import logging
from typing import Any

import redis.asyncio as aioredis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from services.shared.config import settings

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMIT = 1000  # tokens per minute


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter using Redis (Req 20.2).

    Key: rate:{tenant_id}:{api_key}
    Refills at api_rate_limit_per_minute tokens/min.
    Returns 429 with Retry-After header on limit exceeded.
    """

    def __init__(self, app: Any, redis_url: str = settings.redis_url) -> None:
        super().__init__(app)
        self._redis_url = redis_url

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID", "")
        api_key = request.headers.get("X-API-Key", "")

        if not tenant_id or not api_key:
            return await call_next(request)

        allowed, retry_after = await self._check_rate_limit(tenant_id, api_key)
        if not allowed:
            request_id = str(uuid.uuid4())
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "API rate limit exceeded. Please slow down your requests.",
                        "retry_after_seconds": retry_after,
                        "request_id": request_id,
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)

    async def _check_rate_limit(
        self, tenant_id: str, api_key: str
    ) -> tuple[bool, int]:
        """Token bucket check. Returns (allowed, retry_after_seconds)."""
        key = f"rate:{tenant_id}:{api_key}"
        rate_limit = await self._get_rate_limit(tenant_id)
        now = time.time()
        window = 60  # 1 minute

        try:
            redis = aioredis.from_url(self._redis_url, decode_responses=True)
            async with redis.pipeline(transaction=True) as pipe:
                pipe.hgetall(key)
                results = await pipe.execute()

            bucket = results[0]
            if bucket:
                tokens = float(bucket.get("tokens", rate_limit))
                last_refill = float(bucket.get("last_refill", now))
                elapsed = now - last_refill
                refill = (elapsed / window) * rate_limit
                tokens = min(rate_limit, tokens + refill)
            else:
                tokens = float(rate_limit)
                last_refill = now

            if tokens < 1:
                retry_after = math.ceil((1 - tokens) / (rate_limit / window))
                await redis.aclose()
                return False, max(1, retry_after)

            tokens -= 1
            async with redis.pipeline(transaction=True) as pipe:
                pipe.hset(key, mapping={"tokens": tokens, "last_refill": now})
                pipe.expire(key, window * 2)
                await pipe.execute()

            await redis.aclose()
            return True, 0

        except Exception as exc:
            logger.warning("Rate limiter Redis error: %s — allowing request", exc)
            return True, 0

    async def _get_rate_limit(self, tenant_id: str) -> int:
        """Look up tenant rate limit from Redis cache or use default."""
        try:
            redis = aioredis.from_url(self._redis_url, decode_responses=True)
            val = await redis.get(f"tenant_rate_limit:{tenant_id}")
            await redis.aclose()
            if val:
                return int(val)
        except Exception:
            pass
        return DEFAULT_RATE_LIMIT
