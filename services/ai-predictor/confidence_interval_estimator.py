"""Confidence interval estimation for ETA predictions."""

from __future__ import annotations

from datetime import datetime, timedelta


class ConfidenceIntervalEstimator:
    """Compute (lower, upper) bounds around a point ETA estimate."""

    def estimate(
        self,
        eta: datetime,
        uncertainty_hours: float,
    ) -> tuple[datetime, datetime]:
        """Return (eta - uncertainty, eta + uncertainty)."""
        lower = eta - timedelta(hours=uncertainty_hours)
        upper = eta + timedelta(hours=uncertainty_hours)
        # Ensure point estimate is within interval (always true by construction)
        assert lower <= eta <= upper
        return lower, upper
