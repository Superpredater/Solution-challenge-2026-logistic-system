"""REST API — /api/v1/reports router (CSV/JSON exports)."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal
from services.shared.orm_models import CarrierProfileORM, DisruptionORM

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/carrier-performance")
async def carrier_performance(
    start: str = Query(...),
    end: str = Query(...),
    format: str = Query("json", regex="^(json|csv)$"),
    principal=Depends(require_permission("reports:read")),
    session: AsyncSession = Depends(get_session),
) -> Any:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(CarrierProfileORM).where(CarrierProfileORM.tenant_id == UUID(tenant_id))
    )
    rows = result.scalars().all()
    data = [
        {
            "carrier_id": str(r.carrier_id),
            "name": r.name,
            "on_time_rate_90d": r.on_time_rate_90d,
            "on_time_rate_30d": r.on_time_rate_30d,
            "incident_count_90d": r.incident_count_90d,
            "risk_score": r.risk_score,
            "is_high_risk": r.is_high_risk,
        }
        for r in rows
    ]
    if format == "csv":
        return _csv_response(data, "carrier_performance.csv")
    return {"start": start, "end": end, "items": data}


@router.get("/disruption-frequency")
async def disruption_frequency(
    start: str = Query(...),
    end: str = Query(...),
    format: str = Query("json", regex="^(json|csv)$"),
    principal=Depends(require_permission("reports:read")),
    session: AsyncSession = Depends(get_session),
) -> Any:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(DisruptionORM).where(
            DisruptionORM.tenant_id == UUID(tenant_id),
            DisruptionORM.created_at >= datetime.fromisoformat(start),
            DisruptionORM.created_at <= datetime.fromisoformat(end),
        )
    )
    rows = result.scalars().all()
    data = [
        {
            "disruption_id": str(r.disruption_id),
            "disruption_type": r.disruption_type,
            "severity": r.severity,
            "started_at": r.started_at.isoformat(),
        }
        for r in rows
    ]
    if format == "csv":
        return _csv_response(data, "disruption_frequency.csv")
    return {"start": start, "end": end, "items": data}


@router.get("/risk-score-trend")
async def risk_score_trend(
    start: str = Query(...),
    end: str = Query(...),
    format: str = Query("json", regex="^(json|csv)$"),
    principal=Depends(require_permission("reports:read")),
    session: AsyncSession = Depends(get_session),
) -> Any:
    _, tenant_id, _ = principal
    result = await session.execute(
        text(
            """
            SELECT time_bucket('1 hour', recorded_at) AS bucket,
                   AVG(risk_score) AS avg_risk_score,
                   COUNT(*) AS event_count
            FROM risk_score_events
            WHERE tenant_id = :tenant_id
              AND recorded_at BETWEEN :start AND :end
            GROUP BY bucket
            ORDER BY bucket ASC
            """
        ),
        {
            "tenant_id": str(tenant_id),
            "start": start,
            "end": end,
        },
    )
    rows = result.fetchall()
    data = [
        {
            "bucket": row.bucket.isoformat() if hasattr(row.bucket, "isoformat") else str(row.bucket),
            "avg_risk_score": round(row.avg_risk_score, 2),
            "event_count": row.event_count,
        }
        for row in rows
    ]
    if format == "csv":
        return _csv_response(data, "risk_score_trend.csv")
    return {"start": start, "end": end, "items": data}


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
