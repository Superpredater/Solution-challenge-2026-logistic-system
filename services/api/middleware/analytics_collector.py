"""API Gateway — AnalyticsCollector: records API call metrics to TimescaleDB."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AnalyticsCollector:
    """Records API analytics and provides summary queries (Req 20.3)."""

    async def record(
        self,
        tenant_id: str,
        api_key: str,
        endpoint: str,
        status_code: int,
        latency_ms: float,
        session: AsyncSession,
    ) -> None:
        """Insert a single API call record into api_analytics."""
        await session.execute(
            text(
                """
                INSERT INTO api_analytics
                    (id, tenant_id, api_key, endpoint, status_code, latency_ms, recorded_at)
                VALUES
                    (:id, :tenant_id, :api_key, :endpoint, :status_code, :latency_ms, :recorded_at)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "api_key": api_key,
                "endpoint": endpoint,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "recorded_at": datetime.now(timezone.utc),
            },
        )
        await session.commit()

    async def get_summary(
        self,
        tenant_id: str,
        api_key: str,
        days: int,
        session: AsyncSession,
    ) -> dict[str, Any]:
        """Return call volume, error rate, and p50/p95/p99 latency for the given period."""
        result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS call_volume,
                    SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) AS error_rate,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_ms) AS p50_latency_ms,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99_latency_ms
                FROM api_analytics
                WHERE tenant_id = :tenant_id
                  AND api_key = :api_key
                  AND recorded_at >= NOW() - INTERVAL ':days days'
                """
            ),
            {"tenant_id": tenant_id, "api_key": api_key, "days": days},
        )
        row = result.fetchone()
        if row is None:
            return {
                "call_volume": 0,
                "error_rate": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
            }
        return {
            "call_volume": row.call_volume or 0,
            "error_rate": round(row.error_rate or 0.0, 4),
            "p50_latency_ms": round(row.p50_latency_ms or 0.0, 2),
            "p95_latency_ms": round(row.p95_latency_ms or 0.0, 2),
            "p99_latency_ms": round(row.p99_latency_ms or 0.0, 2),
        }
