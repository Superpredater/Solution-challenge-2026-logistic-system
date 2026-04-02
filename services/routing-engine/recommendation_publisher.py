"""Generate and publish reroute recommendations."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.kafka import publish
from services.shared.models import RerouteRecommendation, Route, RouteLeg, Shipment, TransitNodeRef
from .multi_modal_planner import MultiModalPlanner
from .route_graph import RouteGraph
from .route_scorer import RouteScorer
from .eco_ranking_adjuster import EcoRankingAdjuster
from .demand_priority_weighter import DemandPriorityWeighter

logger = logging.getLogger(__name__)

TOPIC = "routing.recommendations"


class RecommendationPublisher:
    """Generate scored recommendations and publish to Kafka."""

    def __init__(self) -> None:
        self._planner = MultiModalPlanner()
        self._scorer = RouteScorer()
        self._eco = EcoRankingAdjuster()
        self._weighter = DemandPriorityWeighter()

    async def generate_and_publish(
        self,
        shipment: Shipment,
        disruption_id: UUID,
        graph: RouteGraph,
        session: AsyncSession,
    ) -> None:
        paths = self._planner.find_routes(
            graph,
            shipment.origin.node_id,
            shipment.destination.node_id,
        )

        if not paths:
            await publish(
                TOPIC,
                {
                    "event": "no_route_available",
                    "shipment_id": str(shipment.shipment_id),
                    "disruption_id": str(disruption_id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                key=str(shipment.shipment_id),
            )
            logger.warning("No viable route for shipment %s", shipment.shipment_id)
            return

        scored = [self._scorer.score(p, shipment.carbon_kg) for p in paths]
        scored = self._eco.rerank(scored, eco_enabled=False)

        for i, (path, score) in enumerate(zip(paths, scored)):
            adjusted_rank = self._weighter.apply_weight(
                score["rank_score"], shipment.demand_priority
            )
            legs = [
                RouteLeg(
                    leg_id=uuid.uuid4(),
                    sequence=j,
                    origin_node_id=path[j - 1][0] if j > 0 else shipment.origin.node_id,
                    destination_node_id=node_id,
                    transport_mode=mode,
                    carrier_id=carrier_id,
                    estimated_duration_hours=duration_h,
                    estimated_cost_usd=cost_usd,
                    carbon_kg=carbon_kg,
                )
                for j, (node_id, mode, carrier_id, duration_h, cost_usd, carbon_kg) in enumerate(path)
            ]
            now = datetime.now(timezone.utc)
            route = Route(
                route_id=uuid.uuid4(),
                tenant_id=shipment.tenant_id,
                shipment_id=shipment.shipment_id,
                legs=legs,
                total_distance_km=0.0,
                total_estimated_duration_hours=score["total_duration_h"],
                total_estimated_cost_usd=score["total_cost_usd"],
                total_carbon_kg=shipment.carbon_kg + score["carbon_delta_kg"],
                is_active=False,
                created_at=now,
            )
            rec = RerouteRecommendation(
                recommendation_id=uuid.uuid4(),
                shipment_id=shipment.shipment_id,
                tenant_id=shipment.tenant_id,
                triggering_risk_score=shipment.risk_score,
                disruption_id=disruption_id,
                candidate_route=route,
                new_eta=shipment.eta,
                cost_delta_usd=score["total_cost_usd"],
                carbon_delta_kg=score["carbon_delta_kg"],
                rank_score=adjusted_rank,
                status="pending",
                created_at=now,
            )
            await publish(
                TOPIC,
                rec.model_dump(mode="json"),
                key=str(shipment.shipment_id),
            )
