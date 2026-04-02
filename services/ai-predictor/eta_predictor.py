"""ETA prediction using a scikit-learn linear regression stub."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from sklearn.linear_model import LinearRegression


class ETAPredictor:
    """Predict ETA with confidence interval using a linear regression stub."""

    # Feature order: distance_km, carrier_risk_score, weather_risk,
    #                num_legs, historical_avg_duration_h
    _FEATURE_NAMES = [
        "distance_km",
        "carrier_risk_score",
        "weather_risk",
        "num_legs",
        "historical_avg_duration_h",
    ]

    def __init__(self) -> None:
        self._model = LinearRegression()
        self._trained = False
        # Seed with a minimal default so predict works before training
        X = np.array([[1000, 20, 10, 3, 48], [5000, 60, 40, 8, 120]])
        y = np.array([50.0, 130.0])
        self._model.fit(X, y)
        self._trained = True

    def _to_features(self, features: dict) -> np.ndarray:
        return np.array(
            [[features.get(f, 0.0) for f in self._FEATURE_NAMES]]
        )

    def predict(
        self, features: dict
    ) -> tuple[datetime, datetime, datetime]:
        """Return (eta, lower_bound, upper_bound)."""
        X = self._to_features(features)
        predicted_hours = float(self._model.predict(X)[0])
        predicted_hours = max(predicted_hours, 0.0)

        # Uncertainty: ±15% of predicted duration, minimum 2h
        uncertainty_h = max(predicted_hours * 0.15, 2.0)

        now = datetime.now(timezone.utc)
        eta = now + timedelta(hours=predicted_hours)
        lower = now + timedelta(hours=predicted_hours - uncertainty_h)
        upper = now + timedelta(hours=predicted_hours + uncertainty_h)
        return eta, lower, upper

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)
        self._trained = True
