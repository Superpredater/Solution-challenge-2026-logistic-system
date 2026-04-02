"""Emissions computation for shipment legs and routes."""

from __future__ import annotations

import math
from uuid import UUID

from services.shared.models import RouteLeg

EMISSIONS_FACTORS: dict[str, float] = {
    "air": 0.82,
    "sea": 0.016,
    "rail": 0.028,
    "road": 0.096,
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class EmissionsComputer:
    """Compute CO₂ emissions for individual legs and full routes."""

    def compute_leg(
        self,
        mode: str,
        distance_km: float,
        carrier_factor: float = 1.0,
    ) -> float:
        """Return kg CO₂ for a single transport leg."""
        factor = EMISSIONS_FACTORS.get(mode, EMISSIONS_FACTORS["road"])
        return factor * distance_km * carrier_factor

    def compute_route(
        self,
        legs: list[RouteLeg],
        node_coords: dict[UUID, tuple[float, float]],
    ) -> float:
        """Return total kg CO₂ for a route given node coordinates."""
        total = 0.0
        for leg in legs:
            origin_coords = node_coords.get(leg.origin_node_id)
            dest_coords = node_coords.get(leg.destination_node_id)
            if origin_coords and dest_coords:
                dist = haversine(
                    origin_coords[0], origin_coords[1],
                    dest_coords[0], dest_coords[1],
                )
            else:
                dist = 0.0
            total += self.compute_leg(leg.transport_mode, dist)
        return total
