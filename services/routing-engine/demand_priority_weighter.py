"""Apply demand-priority weighting to route rank scores."""

from __future__ import annotations


class DemandPriorityWeighter:
    """Multiply rank_score by a priority multiplier (lower = ranked first)."""

    _MULTIPLIERS = {
        "Elevated": 0.9,
        "High": 0.8,
    }

    def apply_weight(self, rank_score: float, demand_priority: str) -> float:
        multiplier = self._MULTIPLIERS.get(demand_priority, 1.0)
        return rank_score * multiplier
