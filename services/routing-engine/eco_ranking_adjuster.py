"""Re-rank routes by carbon when eco mode is enabled."""

from __future__ import annotations


class EcoRankingAdjuster:
    """Sort routes by carbon delta unless it adds >20% time vs fastest."""

    def rerank(self, routes: list[dict], eco_enabled: bool) -> list[dict]:
        if not eco_enabled or not routes:
            return routes

        fastest_time = min(r["total_duration_h"] for r in routes)
        threshold = fastest_time * 1.20

        eco_candidates = [r for r in routes if r["total_duration_h"] <= threshold]
        non_eco = [r for r in routes if r["total_duration_h"] > threshold]

        eco_candidates.sort(key=lambda r: r["carbon_delta_kg"])
        return eco_candidates + non_eco
