"""Digital Twin — SimulationReportGenerator: produces simulation summary reports."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from services.shared.models import ScenarioParameters, SimulationReport

logger = logging.getLogger(__name__)


class SimulationReportGenerator:
    """Generates a SimulationReport from scenario impact data."""

    def generate(
        self,
        scenario_id: UUID,
        tenant_id: UUID,
        scenario_name: str,
        params: ScenarioParameters,
        impact: dict[str, Any],
        duration_seconds: float,
    ) -> SimulationReport:
        """Compute summary metrics and mitigation recommendations."""
        affected_shipments: list[str] = impact.get("affected_shipments", [])
        eta_deviations: dict[str, float] = impact.get("eta_deviations", {})

        affected_count = len(affected_shipments)
        avg_eta_deviation = (
            sum(eta_deviations.values()) / len(eta_deviations)
            if eta_deviations
            else 0.0
        )

        recommendations = self._build_recommendations(params, impact)

        return SimulationReport(
            scenario_id=scenario_id,
            tenant_id=tenant_id,
            scenario_name=scenario_name,
            parameters=params,
            affected_shipment_count=affected_count,
            average_eta_deviation_hours=round(avg_eta_deviation, 2),
            mitigation_recommendations=recommendations,
            completed_at=datetime.now(timezone.utc),
            duration_seconds=round(duration_seconds, 3),
        )

    def _build_recommendations(
        self, params: ScenarioParameters, impact: dict[str, Any]
    ) -> list[str]:
        recommendations: list[str] = []

        if params.node_closures:
            recommendations.append(
                f"Reroute shipments away from {len(params.node_closures)} closed node(s). "
                "Identify alternative transit hubs with available capacity."
            )

        if params.conflict_zone_activations:
            recommendations.append(
                f"Avoid {len(params.conflict_zone_activations)} conflict zone region(s). "
                "Switch to Safe or Caution-rated corridors immediately."
            )

        if params.carrier_capacity_reductions:
            recommendations.append(
                f"Redistribute load from {len(params.carrier_capacity_reductions)} "
                "capacity-reduced carrier(s) to alternative carriers."
            )

        if params.weather_events:
            recommendations.append(
                f"Monitor {len(params.weather_events)} weather-affected region(s). "
                "Pre-position inventory at unaffected distribution centers."
            )

        affected_count = len(impact.get("affected_shipments", []))
        if affected_count > 100:
            recommendations.append(
                f"High impact scenario: {affected_count} shipments affected. "
                "Activate emergency logistics protocols and notify key stakeholders."
            )

        if not recommendations:
            recommendations.append(
                "No critical mitigations required. Monitor situation for escalation."
            )

        return recommendations
