"""Carbon delta calculation between current and alternative routes."""

from __future__ import annotations


class RouteCarbonDeltaCalculator:
    """Compute the CO₂ difference between two route options."""

    def compute_delta(
        self,
        current_carbon_kg: float,
        alternative_carbon_kg: float,
    ) -> float:
        """Return kg CO₂ saved (negative means alternative emits more)."""
        return alternative_carbon_kg - current_carbon_kg
