"""Digital Twin — ImpactCalculator: computes impact of a scenario on shipments."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# ETA deviation per disrupted node on a shipment's route (hours)
_ETA_DEVIATION_PER_DISRUPTED_NODE_HOURS = 4.0
# Risk score increase per disrupted node
_RISK_DELTA_PER_DISRUPTED_NODE = 10.0
# Risk score increase for Restricted war_state
_RISK_DELTA_RESTRICTED = 30.0
# Risk score increase per weather risk delta unit
_RISK_DELTA_PER_WEATHER_UNIT = 0.5


class ImpactCalculator:
    """Computes projected ETA deviations and Risk_Score changes for affected shipments.

    Must complete within 60 seconds for 10,000 shipments (Req 12.3).
    """

    def calculate(
        self,
        original_snapshot: dict[str, Any],
        modified_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        """Return affected_shipments, eta_deviations, and risk_score_changes."""
        # Build lookup maps from modified snapshot
        node_map: dict[str, dict[str, Any]] = {
            n["node_id"]: n for n in modified_snapshot.get("nodes", [])
        }
        orig_node_map: dict[str, dict[str, Any]] = {
            n["node_id"]: n for n in original_snapshot.get("nodes", [])
        }
        carrier_map: dict[str, dict[str, Any]] = {
            c["carrier_id"]: c for c in modified_snapshot.get("carriers", [])
        }
        orig_carrier_map: dict[str, dict[str, Any]] = {
            c["carrier_id"]: c for c in original_snapshot.get("carriers", [])
        }
        route_map: dict[str, dict[str, Any]] = {
            r["route_id"]: r for r in modified_snapshot.get("routes", [])
        }

        affected_shipments: list[str] = []
        eta_deviations: dict[str, float] = {}
        risk_score_changes: dict[str, float] = {}

        for shipment in modified_snapshot.get("shipments", []):
            sid = shipment["shipment_id"]
            route_id = shipment.get("active_route_id", "")
            route = route_map.get(route_id, {})

            eta_delta = 0.0
            risk_delta = 0.0

            # Check carrier capacity reduction impact
            carrier_id = shipment.get("carrier_id", "")
            orig_cap = orig_carrier_map.get(carrier_id, {}).get("capacity_reliability_score", 1.0)
            new_cap = carrier_map.get(carrier_id, {}).get("capacity_reliability_score", 1.0)
            if new_cap < orig_cap:
                cap_reduction = orig_cap - new_cap
                eta_delta += cap_reduction * 8.0  # up to 8h per full capacity loss
                risk_delta += cap_reduction * 20.0

            # Check nodes on route for disruptions / war state changes
            # We approximate by checking origin/destination nodes
            for node_id_key in ("origin_node_id", "destination_node_id"):
                nid = shipment.get(node_id_key, "")
                orig_node = orig_node_map.get(nid, {})
                new_node = node_map.get(nid, {})

                if new_node.get("is_disrupted") and not orig_node.get("is_disrupted"):
                    eta_delta += _ETA_DEVIATION_PER_DISRUPTED_NODE_HOURS
                    risk_delta += _RISK_DELTA_PER_DISRUPTED_NODE

                orig_war = orig_node.get("war_state", "Safe")
                new_war = new_node.get("war_state", "Safe")
                if new_war == "Restricted" and orig_war != "Restricted":
                    risk_delta += _RISK_DELTA_RESTRICTED
                    eta_delta += 12.0  # significant rerouting needed

                weather_delta = new_node.get("weather_risk_delta", 0.0)
                if weather_delta > 0:
                    risk_delta += weather_delta * _RISK_DELTA_PER_WEATHER_UNIT
                    eta_delta += weather_delta * 0.2

            if eta_delta > 0 or risk_delta > 0:
                affected_shipments.append(sid)
                eta_deviations[sid] = round(eta_delta, 2)
                risk_score_changes[sid] = round(min(risk_delta, 100.0), 2)

        logger.info(
            "Impact calculated: %d affected shipments out of %d",
            len(affected_shipments),
            len(modified_snapshot.get("shipments", [])),
        )

        return {
            "affected_shipments": affected_shipments,
            "eta_deviations": eta_deviations,
            "risk_score_changes": risk_score_changes,
        }
