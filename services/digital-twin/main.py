"""Digital Twin — FastAPI service entry point."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.database import AsyncSessionLocal
from services.shared.models import ScenarioParameters, SimulationReport
from services.shared.orm_models import ScenarioORM, SimulationReportORM

from .impact_calculator import ImpactCalculator
from .network_model_builder import NetworkModelBuilder
from .scenario_engine import ScenarioEngine
from .simulation_report_generator import SimulationReportGenerator

logger = logging.getLogger(__name__)

app = FastAPI(title="Digital Twin Service", version="1.0.0")


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "digital-twin"}


@app.post("/api/v1/digital-twin/scenarios", status_code=status.HTTP_202_ACCEPTED)
async def create_scenario(
    body: dict[str, Any],
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Create and run a digital twin scenario simulation."""
    scenario_name = body.get("scenario_name", "Unnamed Scenario")
    tenant_id_str = body.get("tenant_id", str(uuid.uuid4()))
    params_data = body.get("parameters", {})
    params_data["scenario_name"] = scenario_name

    params = ScenarioParameters(**params_data)
    scenario_id = uuid.uuid4()
    tenant_id = uuid.UUID(tenant_id_str)

    # Persist scenario record
    scenario_orm = ScenarioORM(
        scenario_id=scenario_id,
        tenant_id=tenant_id,
        scenario_name=scenario_name,
        parameters=params.model_dump(mode="json"),
        status="running",
        created_at=datetime.now(timezone.utc),
    )
    session.add(scenario_orm)
    await session.commit()

    # Run simulation asynchronously
    asyncio.create_task(
        _run_simulation(scenario_id, tenant_id, scenario_name, params)
    )

    return {
        "scenario_id": str(scenario_id),
        "status": "running",
        "estimated_completion_seconds": 45,
    }


@app.get("/api/v1/digital-twin/scenarios/{scenario_id}/report")
async def get_scenario_report(
    scenario_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Retrieve the simulation report for a completed scenario."""
    from sqlalchemy import select

    result = await session.execute(
        select(SimulationReportORM).where(
            SimulationReportORM.scenario_id == uuid.UUID(scenario_id)
        )
    )
    report_orm = result.scalar_one_or_none()
    if report_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or simulation still running",
        )

    return {
        "scenario_id": str(report_orm.scenario_id),
        "tenant_id": str(report_orm.tenant_id),
        "scenario_name": report_orm.scenario_name,
        "parameters": report_orm.parameters,
        "affected_shipment_count": report_orm.affected_shipment_count,
        "average_eta_deviation_hours": report_orm.average_eta_deviation_hours,
        "mitigation_recommendations": report_orm.mitigation_recommendations,
        "completed_at": report_orm.completed_at.isoformat(),
        "duration_seconds": report_orm.duration_seconds,
    }


async def _run_simulation(
    scenario_id: uuid.UUID,
    tenant_id: uuid.UUID,
    scenario_name: str,
    params: ScenarioParameters,
) -> None:
    """Background task: build snapshot, apply scenario, calculate impact, save report."""
    start = time.monotonic()
    try:
        async with AsyncSessionLocal() as session:
            builder = NetworkModelBuilder()
            engine = ScenarioEngine()
            calculator = ImpactCalculator()
            reporter = SimulationReportGenerator()

            snapshot = await builder.build_snapshot(session)
            modified = engine.apply_scenario(snapshot, params)
            impact = calculator.calculate(snapshot, modified)
            duration = time.monotonic() - start

            report = reporter.generate(
                scenario_id=scenario_id,
                tenant_id=tenant_id,
                scenario_name=scenario_name,
                params=params,
                impact=impact,
                duration_seconds=duration,
            )

            report_orm = SimulationReportORM(
                report_id=uuid.uuid4(),
                scenario_id=scenario_id,
                tenant_id=tenant_id,
                scenario_name=scenario_name,
                parameters=params.model_dump(mode="json"),
                affected_shipment_count=report.affected_shipment_count,
                average_eta_deviation_hours=report.average_eta_deviation_hours,
                mitigation_recommendations=report.mitigation_recommendations,
                completed_at=report.completed_at,
                duration_seconds=report.duration_seconds,
            )
            session.add(report_orm)

            # Update scenario status
            from sqlalchemy import select, update
            await session.execute(
                update(ScenarioORM)
                .where(ScenarioORM.scenario_id == scenario_id)
                .values(status="completed")
            )
            await session.commit()

        logger.info(
            "Simulation %s completed in %.2fs, %d affected shipments",
            scenario_id,
            duration,
            report.affected_shipment_count,
        )
    except Exception as exc:
        logger.error("Simulation %s failed: %s", scenario_id, exc)
        async with AsyncSessionLocal() as session:
            from sqlalchemy import update
            await session.execute(
                update(ScenarioORM)
                .where(ScenarioORM.scenario_id == scenario_id)
                .values(status="failed")
            )
            await session.commit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8007)
