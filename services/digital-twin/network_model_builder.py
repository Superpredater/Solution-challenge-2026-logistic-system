"""Digital Twin — NetworkModelBuilder: builds a snapshot of the supply chain network."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.orm_models import (
    CarrierProfileORM,
    RouteORM,
    RouteLegORM,
    ShipmentORM,
    TransitNodeORM,
)

logger = logging.getLogger(__name__)


class NetworkModelBuilder:
    """Constructs a point-in-time snapshot of the supply chain network.

    Supports up to 10,000 shipments per snapshot (Req 12.2).
    """

    MAX_SHIPMENTS = 10_000

    async def build_snapshot(self, session: AsyncSession) -> dict[str, Any]:
        """Query PostgreSQL for all active shipments, routes, nodes, and carriers.

        Returns a dict with keys: shipments, routes, nodes, carriers.
        """
        shipments = await self._load_shipments(session)
        routes = await self._load_routes(session, shipments)
        nodes = await self._load_nodes(session)
        carriers = await self._load_carriers(session)

        logger.info(
            "Snapshot built: %d shipments, %d routes, %d nodes, %d carriers",
            len(shipments),
            len(routes),
            len(nodes),
            len(carriers),
        )
        return {
            "shipments": shipments,
            "routes": routes,
            "nodes": nodes,
            "carriers": carriers,
        }

    async def _load_shipments(self, session: AsyncSession) -> list[dict[str, Any]]:
        result = await session.execute(
            select(ShipmentORM)
            .where(ShipmentORM.status.in_(["In_Transit", "Delayed", "Connectivity_Impaired"]))
            .limit(self.MAX_SHIPMENTS)
        )
        rows = result.scalars().all()
        return [
            {
                "shipment_id": str(r.shipment_id),
                "tenant_id": str(r.tenant_id),
                "origin_node_id": str(r.origin_node_id),
                "destination_node_id": str(r.destination_node_id),
                "active_route_id": str(r.active_route_id),
                "carrier_id": str(r.carrier_id),
                "status": r.status,
                "risk_score": r.risk_score,
                "eta": r.eta.isoformat(),
                "demand_priority": r.demand_priority,
                "carbon_kg": r.carbon_kg,
            }
            for r in rows
        ]

    async def _load_routes(
        self, session: AsyncSession, shipments: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        route_ids = [s["active_route_id"] for s in shipments]
        if not route_ids:
            return []
        result = await session.execute(
            select(RouteORM).where(RouteORM.route_id.in_(route_ids))
        )
        routes = result.scalars().all()
        return [
            {
                "route_id": str(r.route_id),
                "shipment_id": str(r.shipment_id),
                "tenant_id": str(r.tenant_id),
                "total_distance_km": r.total_distance_km,
                "total_estimated_duration_hours": r.total_estimated_duration_hours,
                "total_estimated_cost_usd": r.total_estimated_cost_usd,
                "total_carbon_kg": r.total_carbon_kg,
                "is_active": r.is_active,
            }
            for r in routes
        ]

    async def _load_nodes(self, session: AsyncSession) -> list[dict[str, Any]]:
        result = await session.execute(select(TransitNodeORM))
        rows = result.scalars().all()
        return [
            {
                "node_id": str(r.node_id),
                "tenant_id": str(r.tenant_id),
                "name": r.name,
                "node_type": r.node_type,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "region_id": str(r.region_id),
                "is_disrupted": r.is_disrupted,
                "war_state": r.war_state,
                "current_dwell_time_hours": r.current_dwell_time_hours,
                "p90_dwell_time_hours": r.p90_dwell_time_hours,
            }
            for r in rows
        ]

    async def _load_carriers(self, session: AsyncSession) -> list[dict[str, Any]]:
        result = await session.execute(select(CarrierProfileORM))
        rows = result.scalars().all()
        return [
            {
                "carrier_id": str(r.carrier_id),
                "tenant_id": str(r.tenant_id),
                "name": r.name,
                "risk_score": r.risk_score,
                "on_time_rate_90d": r.on_time_rate_90d,
                "on_time_rate_30d": r.on_time_rate_30d,
                "capacity_reliability_score": r.capacity_reliability_score,
                "is_high_risk": r.is_high_risk,
            }
            for r in rows
        ]
