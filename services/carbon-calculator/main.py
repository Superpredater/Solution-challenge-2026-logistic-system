"""Carbon Calculator service — minimal FastAPI app."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.database import get_session
from .tenant_emissions_aggregator import TenantEmissionsAggregator

app = FastAPI(title="Carbon Calculator", version="1.0.0")

_aggregator = TenantEmissionsAggregator()


@app.get("/api/v1/carbon/tenants/{tenant_id}/emissions")
async def get_tenant_emissions(
    tenant_id: UUID,
    start: datetime = Query(...),
    end: datetime = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    total = await _aggregator.aggregate(tenant_id, start, end, session)
    return {"tenant_id": str(tenant_id), "total_carbon_kg": total, "start": start, "end": end}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
