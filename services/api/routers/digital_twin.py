"""REST API — /api/v1/digital-twin router."""

from __future__ import annotations

import asyncio
import copy
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal
from services.shared.models import ScenarioParameters
from services.shared.orm_models import (
    CarrierProfileORM,
    ScenarioORM,
    ShipmentORM,
    SimulationReportORM,
    TransitNodeORM,
)

router = APIRouter(prefix="/api/v1/digital-twin", tags=["digital-twin"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/scenarios", status_code=status.HTTP_202_ACCEPTED)
async def create_scenario(
    body: dict[str, Any],
    principal=Depends(require_permission("scenarios:run")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    scenario_name = body.get("scenario_name", "Unnamed Scenario")
    params_data = body.get("parameters", {})
    params_data["scenario_name"] = scenario_name
    params = ScenarioParameters(**params_data)

    scenario_id = uuid.uuid4()
    orm = ScenarioORM(
        scenario_id=scenario_id,
        tenant_id=UUID(tenant_id),
        scenario_name=scenario_name,
        parameters=params.model_dump(mode="json"),
        status="running",
        created_at=datetime.now(timezone.utc),
    )
    session.add(orm)
    await session.commit()

    asyncio.create_task(_run_simulation(scenario_id, UUID(tenant_id), scenario_name, params))

    return {
        "scenario_id": str(scenario_id),
        "status": "running",
        "estimated_completion_seconds": 45,
    }


@router.get("/scenarios/{scenario_id}")
async def get_scenario(
    scenario_id: UUID,
    principal=Depends(require_permission("scenarios:run")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(ScenarioORM).where(
            ScenarioORM.scenario_id == scenario_id,
            ScenarioORM.tenant_id == UUID(tenant_id),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {
        "scenario_id": str(row.scenario_id),
        "scenario_name": row.scenario_name,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
    }


@router.get("/scenarios/{scenario_id}/report")
async def get_scenario_report(
    scenario_id: UUID,
    principal=Depends(require_permission("scenarios:run")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _, tenant_id, _ = principal
    result = await session.execute(
        select(SimulationReportORM).where(
            SimulationReportORM.scenario_id == scenario_id,
            SimulationReportORM.tenant_id == UUID(tenant_id),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found or simulation still running")
    return {
        "scenario_id": str(row.scenario_id),
        "scenario_name": row.scenario_name,
        "affected_shipment_count": row.affected_shipment_count,
        "average_eta_deviation_hours": row.average_eta_deviation_hours,
        "mitigation_recommendations": row.mitigation_recommendations,
        "completed_at": row.completed_at.isoformat(),
        "duration_seconds": row.duration_seconds,
    }


async def _run_simulation(
    scenario_id: UUID,
    tenant_id: UUID,
    scenario_name: str,
    params: ScenarioParameters,
) -> None:
    """Background simulation: build snapshot, apply scenario, calculate impact, save report."""
    start = time.monotonic()
    try:
        async with AsyncSessionLocal() as session:
            # Build snapshot
            shipments_result = await session.execute(
                select(ShipmentORM)
                .where(ShipmentORM.tenant_id == tenant_id)
                .where(ShipmentORM.status.in_(["In_Transit", "Delayed", "Connectivity_Impaired"]))
                .limit(10_000)
            )
            shipments = [
                {
                    "shipment_id": str(r.shipment_id),
                    "origin_node_id": str(r.origin_node_id),
                    "destination_node_id": str(r.destination_node_id),
                    "carrier_id": str(r.carrier_id),
                    "risk_score": r.risk_score,
                }
                for r in shipments_result.scalars().all()
            ]

            nodes_result = await session.execute(select(TransitNodeORM))
            nodes: dict[str, dict[str, Any]] = {
                str(r.node_id): {
                    "node_id": str(r.node_id),
                    "region_id": str(r.region_id),
                    "is_disrupted": r.is_disrupted,
                    "war_state": r.war_state,
                }
                for r in nodes_result.scalars().all()
            }

            carriers_result = await session.execute(select(CarrierProfileORM))
            carriers: dict[str, dict[str, Any]] = {
                str(r.carrier_id): {
                    "carrier_id": str(r.carrier_id),
                    "capacity_reliability_score": r.capacity_reliability_score,
                }
                for r in carriers_result.scalars().all()
            }

            # Apply scenario to copies
            modified_nodes = copy.deepcopy(nodes)
            modified_carriers = copy.deepcopy(carriers)

            closure_ids = {str(nid) for nid in params.node_closures}
            for nid, node in modified_nodes.items():
                if nid in closure_ids:
                    node["is_disrupted"] = True

            conflict_ids = {str(rid) for rid in params.conflict_zone_activations}
            for nid, node in modified_nodes.items():
                if node.get("region_id") in conflict_ids:
                    node["war_state"] = "Restricted"

            for item in params.carrier_capacity_reductions:
                cid = str(item.get("carrier_id", ""))
                pct = float(item.get("reduction_pct", 0))
                if cid in modified_carriers:
                    modified_carriers[cid]["capacity_reliability_score"] = max(
                        0.0,
                        modified_carriers[cid]["capacity_reliability_score"] * (1 - pct / 100),
                    )

            # Calculate impact
            affected: list[str] = []
            eta_deviations: dict[str, float] = {}

            for s in shipments:
                sid = s["shipment_id"]
                eta_delta = 0.0
                risk_delta = 0.0

                for nk in ("origin_node_id", "destination_node_id"):
                    nid = s.get(nk, "")
                    orig = nodes.get(nid, {})
                    mod = modified_nodes.get(nid, {})
                    if mod.get("is_disrupted") and not orig.get("is_disrupted"):
                        eta_delta += 4.0
                        risk_delta += 10.0
                    if mod.get("war_state") == "Restricted" and orig.get("war_state") != "Restricted":
                        eta_delta += 12.0
                        risk_delta += 30.0

                cid = s.get("carrier_id", "")
                orig_cap = carriers.get(cid, {}).get("capacity_reliability_score", 1.0)
                mod_cap = modified_carriers.get(cid, {}).get("capacity_reliability_score", 1.0)
                if mod_cap < orig_cap:
                    cap_loss = orig_cap - mod_cap
                    eta_delta += cap_loss * 8.0
                    risk_delta += cap_loss * 20.0

                if eta_delta > 0 or risk_delta > 0:
                    affected.append(sid)
                    eta_deviations[sid] = round(eta_delta, 2)

            duration = time.monotonic() - start
            avg_eta = sum(eta_deviations.values()) / len(eta_deviations) if eta_deviations else 0.0

            recs: list[str] = []
            if params.node_closures:
                recs.append(f"Reroute away from {len(params.node_closures)} closed node(s).")
            if params.conflict_zone_activations:
                recs.append(f"Avoid {len(params.conflict_zone_activations)} conflict zone(s).")
            if params.carrier_capacity_reductions:
                recs.append(
                    f"Redistribute load from {len(params.carrier_capacity_reductions)} reduced carrier(s)."
                )
            if not recs:
                recs.append("No critical mitigations required.")

            session.add(
                SimulationReportORM(
                    report_id=uuid.uuid4(),
                    scenario_id=scenario_id,
                    tenant_id=tenant_id,
                    scenario_name=scenario_name,
                    parameters=params.model_dump(mode="json"),
                    affected_shipment_count=len(affected),
                    average_eta_deviation_hours=round(avg_eta, 2),
                    mitigation_recommendations=recs,
                    completed_at=datetime.now(timezone.utc),
                    duration_seconds=round(duration, 3),
                )
            )
            await session.execute(
                update(ScenarioORM)
                .where(ScenarioORM.scenario_id == scenario_id)
                .values(status="completed")
            )
            await session.commit()

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Simulation %s failed: %s", scenario_id, exc)
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(ScenarioORM)
                .where(ScenarioORM.scenario_id == scenario_id)
                .values(status="failed")
            )
            await session.commit()
