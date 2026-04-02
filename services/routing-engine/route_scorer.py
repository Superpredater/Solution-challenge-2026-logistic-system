"""Score and rank candidate routes."""

from __future__ import annotations

from .multi_modal_planner import PathNode


class RouteScorer:
    """Score a path on cost, time, and carbon delta."""

    # Weights for rank_score (must sum to 1.0)
    W_COST = 0.4
    W_TIME = 0.4
    W_CARBON = 0.2

    def score(
        self,
        path: list[PathNode],
        current_carbon_kg: float,
    ) -> dict:
        total_duration_h = sum(p[3] for p in path)
        total_cost_usd = sum(p[4] for p in path)
        total_carbon_kg = sum(p[5] for p in path)
        carbon_delta_kg = total_carbon_kg - current_carbon_kg

        # Normalise each dimension to [0, 1] using simple ratio
        # (in production these would be normalised against a fleet-wide baseline)
        norm_cost = total_cost_usd / max(total_cost_usd, 1.0)
        norm_time = total_duration_h / max(total_duration_h, 1.0)
        norm_carbon = max(carbon_delta_kg + current_carbon_kg, 0.0) / max(current_carbon_kg, 1.0)

        rank_score = (
            self.W_COST * norm_cost
            + self.W_TIME * norm_time
            + self.W_CARBON * norm_carbon
        )

        return {
            "total_duration_h": total_duration_h,
            "total_cost_usd": total_cost_usd,
            "carbon_delta_kg": carbon_delta_kg,
            "rank_score": rank_score,
        }
