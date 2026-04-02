"""Monitor shipment GPS positions for route deviations."""

from __future__ import annotations

import math


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RouteDeviationMonitor:
    """Detect when a shipment has deviated from its planned waypoints."""

    def check_deviation(
        self,
        current_lat: float,
        current_lon: float,
        planned_waypoints: list[tuple[float, float]],
        threshold_km: float = 50.0,
    ) -> bool:
        """Return True if the shipment is more than threshold_km from every waypoint."""
        if not planned_waypoints:
            return False
        min_dist = min(
            _haversine(current_lat, current_lon, wp[0], wp[1])
            for wp in planned_waypoints
        )
        return min_dist > threshold_km
