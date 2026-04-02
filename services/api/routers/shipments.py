"""REST API — /api/v1/shipments router."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal
from services.shared.orm_models import (
    RerouteRecommendationORM,
    RiskScoreEventORM,
    ShipmentORM,
)

router = APIRouter(prefix="/api/v1/shipments", tags=["shipments"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_shipments(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    principal=Depends(require_permission("shipments:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    offset = (page - 1) * page_size
    result = await session.execute(
        select(ShipmentORM)
        .where(ShipmentORM.tenant_id == UUID(tenant_id))
        .order_by(ShipmentORM.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = result.scalars().all()
    return {
        "page": page,
        "page_size": page_size,
        "items": [_shipment_dict(r) for r in rows],
    }


@router.get("/{shipment_id}")
async def get_shipment(
    shipment_id: UUID,
    principal=Depends(require_permission("shipments:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(ShipmentORM).where(
            ShipmentORM.shipment_id == shipment_id,
            ShipmentORM.tenant_id == UUID(tenant_id),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return _shipment_dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_shipment(
    body: dict[str, Any],
    principal=Depends(require_permission("recommendations:approve")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from datetime import datetime, timezone
    import uuid as _uuid

    _, tenant_id, _ = principal
    now = datetime.now(timezone.utc)
    orm = ShipmentORM(
        shipment_id=_uuid.uuid4(),
        tenant_id=UUID(tenant_id),
        origin_node_id=UUID(body["origin_node_id"]),
        origin_node_name=body.get("origin_node_name", ""),
        destination_node_id=UUID(body["destination_node_id"]),
        destination_node_name=body.get("destination_node_name", ""),
        active_route_id=UUID(body["active_route_id"]),
        carrier_id=UUID(body["carrier_id"]),
        status=body.get("status", "In_Transit"),
        risk_score=body.get("risk_score", 0.0),
        risk_score_updated_at=now,
        eta=datetime.fromisoformat(body["eta"]),
        eta_lower=datetime.fromisoformat(body.get("eta_lower", body["eta"])),
        eta_upper=datetime.fromisoformat(body.get("eta_upper", body["eta"])),
        demand_priority=body.get("demand_priority", "Normal"),
        carbon_kg=body.get("carbon_kg", 0.0),
        created_at=now,
        updated_at=now,
    )
    session.add(orm)
    await session.commit()
    return _shipment_dict(orm)


@router.patch("/{shipment_id}")
async def update_shipment(
    shipment_id: UUID,
    body: dict[str, Any],
    principal=Depends(require_permission("recommendations:approve")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from datetime import datetime, timezone

    _, tenant_id, _ = principal
    result = await session.execute(
        select(ShipmentORM).where(
            ShipmentORM.shipment_id == shipment_id,
            ShipmentORM.tenant_id == UUID(tenant_id),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    if "status" in body:
        row.status = body["status"]
    row.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return _shipment_dict(row)


@router.get("/{shipment_id}/risk-history")
async def get_risk_history(
    shipment_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    principal=Depends(require_permission("shipments:read")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(RiskScoreEventORM)
        .where(
            RiskScoreEventORM.shipment_id == shipment_id,
            RiskScoreEventORM.tenant_id == UUID(tenant_id),
        )
        .order_by(RiskScoreEventORM.recorded_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "event_id": str(r.event_id),
            "risk_score": r.risk_score,
            "weather_component": r.weather_component,
            "operational_component": r.operational_component,
            "war_state_component": r.war_state_component,
            "geopolitical_component": r.geopolitical_component,
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/{shipment_id}/recommendations")
async def get_recommendations(
    shipment_id: UUID,
    principal=Depends(require_permission("shipments:read")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(RerouteRecommendationORM)
        .where(
            RerouteRecommendationORM.shipment_id == shipment_id,
            RerouteRecommendationORM.tenant_id == UUID(tenant_id),
        )
        .order_by(RerouteRecommendationORM.created_at.desc())
    )
    rows = result.scalars().all()
    return [_recommendation_dict(r) for r in rows]


@router.post("/{shipment_id}/recommendations/{rec_id}/accept")
async def accept_recommendation(
    shipment_id: UUID,
    rec_id: UUID,
    body: dict[str, Any],
    principal=Depends(require_permission("recommendations:approve")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from datetime import datetime, timezone

    _, tenant_id, stakeholder_id = principal
    result = await session.execute(
        select(RerouteRecommendationORM).where(
            RerouteRecommendationORM.recommendation_id == rec_id,
            RerouteRecommendationORM.shipment_id == shipment_id,
            RerouteRecommendationORM.tenant_id == UUID(tenant_id),
        )
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.status = "accepted"
    rec.decided_at = datetime.now(timezone.utc)
    rec.decided_by = UUID(stakeholder_id)
    await session.commit()
    return {"shipment_id": str(shipment_id), "recommendation_id": str(rec_id), "status": "accepted"}


@router.post("/{shipment_id}/recommendations/{rec_id}/reject")
async def reject_recommendation(
    shipment_id: UUID,
    rec_id: UUID,
    body: dict[str, Any],
    principal=Depends(require_permission("recommendations:reject")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from datetime import datetime, timezone

    _, tenant_id, stakeholder_id = principal
    result = await session.execute(
        select(RerouteRecommendationORM).where(
            RerouteRecommendationORM.recommendation_id == rec_id,
            RerouteRecommendationORM.shipment_id == shipment_id,
            RerouteRecommendationORM.tenant_id == UUID(tenant_id),
        )
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.status = "rejected"
    rec.decided_at = datetime.now(timezone.utc)
    rec.decided_by = UUID(stakeholder_id)
    await session.commit()
    return {"shipment_id": str(shipment_id), "recommendation_id": str(rec_id), "status": "rejected"}


@router.get("/{shipment_id}/ai-explanation")
async def get_ai_explanation(
    shipment_id: UUID,
    principal=Depends(require_permission("ai:query")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(ShipmentORM).where(
            ShipmentORM.shipment_id == shipment_id,
            ShipmentORM.tenant_id == UUID(tenant_id),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    # AI explanation is fetched from ai_interaction_logs in production
    return {
        "shipment_id": str(shipment_id),
        "explanation": f"Risk score {row.risk_score:.1f} based on current route conditions.",
        "fallback_used": True,
    }


@router.get("/{shipment_id}/carbon")
async def get_carbon_summary(
    shipment_id: UUID,
    principal=Depends(require_permission("shipments:read")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(ShipmentORM).where(
            ShipmentORM.shipment_id == shipment_id,
            ShipmentORM.tenant_id == UUID(tenant_id),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return {"shipment_id": str(shipment_id), "carbon_kg": row.carbon_kg}


def _shipment_dict(r: ShipmentORM) -> dict[str, Any]:
    return {
        "shipment_id": str(r.shipment_id),
        "tenant_id": str(r.tenant_id),
        "status": r.status,
        "risk_score": r.risk_score,
        "risk_score_updated_at": r.risk_score_updated_at.isoformat(),
        "eta": r.eta.isoformat(),
        "eta_confidence_interval": [r.eta_lower.isoformat(), r.eta_upper.isoformat()],
        "active_route_id": str(r.active_route_id),
        "carrier_id": str(r.carrier_id),
        "demand_priority": r.demand_priority,
        "carbon_kg": r.carbon_kg,
    }


def _recommendation_dict(r: RerouteRecommendationORM) -> dict[str, Any]:
    return {
        "recommendation_id": str(r.recommendation_id),
        "shipment_id": str(r.shipment_id),
        "triggering_risk_score": r.triggering_risk_score,
        "cost_delta_usd": r.cost_delta_usd,
        "carbon_delta_kg": r.carbon_delta_kg,
        "rank_score": r.rank_score,
        "status": r.status,
        "new_eta": r.new_eta.isoformat(),
        "created_at": r.created_at.isoformat(),
    }
