"""REST API — /api/v1/analytics router (historical analytics with TimescaleDB)."""

from __future__ import annotations

import csv
import io
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_QUERY_TIMEOUT_MS = 25_000  # 25 seconds


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/risk-score-trend")
async def risk_score_trend(
    tenant_id: str = Query(...),
    start: str = Query(...),
    end: str = Query(...),
    bucket_interval: str = Query("1 hour"),
    format: str = Query("json", regex="^(json|csv)$"),
    principal=Depends(require_permission("analytics:read")),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """TimescaleDB time_bucket query for risk score trend (25s timeout)."""
    _, caller_tenant_id, _ = principal
    # Enforce tenant scoping
    effective_tenant_id = caller_tenant_id

    await session.execute(
        text(f"SET LOCAL statement_timeout = '{_QUERY_TIMEOUT_MS}'")
    )
    result = await session.execute(
        text(
            """
            SELECT
                time_bucket(:bucket_interval, recorded_at) AS bucket,
                AVG(risk_score)                            AS avg_risk_score,
                MIN(risk_score)                            AS min_risk_score,
                MAX(risk_score)                            AS max_risk_score,
                COUNT(*)                                   AS event_count
            FROM risk_score_events
            WHERE tenant_id = :tenant_id
              AND recorded_at BETWEEN :start AND :end
            GROUP BY bucket
            ORDER BY bucket ASC
            """
        ),
        {
            "bucket_interval": bucket_interval,
            "tenant_id": effective_tenant_id,
            "start": start,
            "end": end,
        },
    )
    rows = result.fetchall()
    data = [
        {
            "bucket": _iso(row.bucket),
            "avg_risk_score": round(row.avg_risk_score, 2),
            "min_risk_score": round(row.min_risk_score, 2),
            "max_risk_score": round(row.max_risk_score, 2),
            "event_count": row.event_count,
        }
        for row in rows
    ]
    if format == "csv":
        return _csv_response(data, "risk_score_trend.csv")
    return {"tenant_id": effective_tenant_id, "start": start, "end": end, "items": data}


@router.get("/carrier-performance")
async def carrier_performance(
    start: str = Query(...),
    end: str = Query(...),
    format: str = Query("json", regex="^(json|csv)$"),
    principal=Depends(require_permission("analytics:read")),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Carrier performance from materialized view."""
    _, tenant_id, _ = principal

    await session.execute(
        text(f"SET LOCAL statement_timeout = '{_QUERY_TIMEOUT_MS}'")
    )
    result = await session.execute(
        text(
            """
            SELECT
                cp.carrier_id::text,
                cp.name,
                cp.on_time_rate_90d,
                cp.on_time_rate_30d,
                cp.incident_count_90d,
                cp.risk_score,
                cp.is_high_risk
            FROM carrier_profiles cp
            WHERE cp.tenant_id = :tenant_id
            ORDER BY cp.risk_score DESC
            """
        ),
        {"tenant_id": tenant_id},
    )
    rows = result.fetchall()
    data = [
        {
            "carrier_id": row.carrier_id,
            "name": row.name,
            "on_time_rate_90d": row.on_time_rate_90d,
            "on_time_rate_30d": row.on_time_rate_30d,
            "incident_count_90d": row.incident_count_90d,
            "risk_score": row.risk_score,
            "is_high_risk": row.is_high_risk,
        }
        for row in rows
    ]
    if format == "csv":
        return _csv_response(data, "carrier_performance.csv")
    return {"start": start, "end": end, "items": data}


@router.get("/disruption-frequency")
async def disruption_frequency(
    start: str = Query(...),
    end: str = Query(...),
    format: str = Query("json", regex="^(json|csv)$"),
    principal=Depends(require_permission("analytics:read")),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Disruption count by node within the given time range."""
    _, tenant_id, _ = principal

    await session.execute(
        text(f"SET LOCAL statement_timeout = '{_QUERY_TIMEOUT_MS}'")
    )
    result = await session.execute(
        text(
            """
            SELECT
                disruption_type,
                severity,
                COUNT(*) AS disruption_count,
                MIN(started_at) AS first_occurrence,
                MAX(started_at) AS last_occurrence
            FROM disruptions
            WHERE tenant_id = :tenant_id
              AND created_at BETWEEN :start AND :end
            GROUP BY disruption_type, severity
            ORDER BY disruption_count DESC
            """
        ),
        {"tenant_id": tenant_id, "start": start, "end": end},
    )
    rows = result.fetchall()
    data = [
        {
            "disruption_type": row.disruption_type,
            "severity": row.severity,
            "disruption_count": row.disruption_count,
            "first_occurrence": _iso(row.first_occurrence),
            "last_occurrence": _iso(row.last_occurrence),
        }
        for row in rows
    ]
    if format == "csv":
        return _csv_response(data, "disruption_frequency.csv")
    return {"start": start, "end": end, "items": data}


def _iso(val: Any) -> str:
    if val is None:
        return ""
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _csv_response(data: list[dict[str, Any]], filename: str) -> StreamingResponse:
    if not data:
        return StreamingResponse(
            iter([""]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
