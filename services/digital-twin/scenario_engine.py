"""Digital Twin — ScenarioEngine: applies scenario parameters to a network snapshot."""

from __future__ import annotations

import copy
import logging
from typing import Any

from services.shared.models import ScenarioParameters

logger = logging.getLogger(__name__)


class ScenarioEngine:
    """Applies scenario parameters to a copy of the network snapshot."""

    def apply_scenario(
        self, snapshot: dict[str, Any], params: ScenarioParameters
    ) -> dict[str, Any]:
        """Apply scenario parameters to a deep copy of the snapshot.

        Modifies:
        - node_closures: marks nodes as disrupted
        - conflict_zone_activations: sets war_state=Restricted for affected regions
        - carrier_capacity_reductions: reduces carrier capacity by percentage
        - weather_events: adds weather risk to affected regions
        """
        modified = copy.deepcopy(snapshot)

        self._apply_node_closures(modified, params)
        self._apply_conflict_zones(modified, params)
        self._apply_carrier_capacity_reductions(modified, params)
        self._apply_weather_events(modified, params)

        return modified

    def _apply_node_closures(
        self, snapshot: dict[str, Any], params: ScenarioParameters
    ) -> None:
        closure_ids = {str(nid) for nid in params.node_closures}
        for node in snapshot.get("nodes", []):
            if node["node_id"] in closure_ids:
                node["is_disrupted"] = True
                logger.debug("Node %s marked as disrupted", node["node_id"])

    def _apply_conflict_zones(
        self, snapshot: dict[str, Any], params: ScenarioParameters
    ) -> None:
        conflict_region_ids = {str(rid) for rid in params.conflict_zone_activations}
        for node in snapshot.get("nodes", []):
            if node.get("region_id") in conflict_region_ids:
                node["war_state"] = "Restricted"
                logger.debug(
                    "Node %s war_state set to Restricted (region %s)",
                    node["node_id"],
                    node["region_id"],
                )

    def _apply_carrier_capacity_reductions(
        self, snapshot: dict[str, Any], params: ScenarioParameters
    ) -> None:
        reductions: dict[str, float] = {}
        for item in params.carrier_capacity_reductions:
            carrier_id = str(item.get("carrier_id", ""))
            pct = float(item.get("reduction_pct", 0))
            reductions[carrier_id] = pct

        for carrier in snapshot.get("carriers", []):
            cid = carrier["carrier_id"]
            if cid in reductions:
                pct = reductions[cid]
                carrier["capacity_reliability_score"] = max(
                    0.0,
                    carrier.get("capacity_reliability_score", 1.0) * (1.0 - pct / 100.0),
                )
                logger.debug(
                    "Carrier %s capacity reduced by %.1f%%", cid, pct
                )

    def _apply_weather_events(
        self, snapshot: dict[str, Any], params: ScenarioParameters
    ) -> None:
        weather_region_ids: dict[str, float] = {}
        for event in params.weather_events:
            region_id = str(event.get("region_id", ""))
            risk_delta = float(event.get("risk_delta", 10.0))
            weather_region_ids[region_id] = risk_delta

        for shipment in snapshot.get("shipments", []):
            # Attach weather risk metadata for ImpactCalculator to use
            shipment.setdefault("weather_risk_delta", 0.0)

        for node in snapshot.get("nodes", []):
            rid = node.get("region_id", "")
            if rid in weather_region_ids:
                node.setdefault("weather_risk_delta", 0.0)
                node["weather_risk_delta"] = weather_region_ids[rid]
                logger.debug(
                    "Node %s weather risk delta set to %.1f",
                    node["node_id"],
                    node["weather_risk_delta"],
                )
