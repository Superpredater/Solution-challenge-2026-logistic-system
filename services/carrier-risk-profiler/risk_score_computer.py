"""Computes a carrier risk score (0–100) from performance metrics."""

from __future__ import annotations


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


class RiskScoreComputer:
    """
    Produces a carrier risk score (0–100, higher = riskier).

    Formula:
        clamp(
            (1 - on_time_rate_90d) * 50
            + min(incident_count_90d, 10) * 3
            + (1 - capacity_reliability) * 20,
            0, 100
        )
    """

    def compute(
        self,
        on_time_rate_90d: float,
        incident_count_90d: int,
        capacity_reliability: float,
    ) -> float:
        raw = (
            (1.0 - on_time_rate_90d) * 50.0
            + min(incident_count_90d, 10) * 3.0
            + (1.0 - capacity_reliability) * 20.0
        )
        return _clamp(raw)
