"""Aggregates dimension risk scores into a unified Risk_Score."""

from __future__ import annotations

from services.shared.models import RiskWeights


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


class RiskAggregator:
    """Combines weather, operational, war-state, and geopolitical scores."""

    def compute(
        self,
        weather: float,
        operational: float,
        war_state: float,
        geopolitical: float,
        weights: RiskWeights,
    ) -> float:
        """
        Formula:
            clamp(
                w_weather * weather
                + w_operational * operational
                + w_war * war_state
                + w_geopolitical * geopolitical,
                0, 100
            )
        """
        raw = (
            weights.w_weather * weather
            + weights.w_operational * operational
            + weights.w_war * war_state
            + weights.w_geopolitical * geopolitical
        )
        return _clamp(raw)
