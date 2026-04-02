"""Risk dimension evaluators for the Risk Engine."""

from __future__ import annotations


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


class WeatherRiskEvaluator:
    """Scores weather impact on a route segment (0–100)."""

    # Severity label → base score mapping
    _SEVERITY_MAP: dict[str, float] = {
        "none": 0.0,
        "low": 15.0,
        "moderate": 35.0,
        "high": 65.0,
        "severe": 85.0,
        "extreme": 100.0,
    }

    def evaluate(self, weather_data: dict) -> float:
        """
        Returns a 0–100 weather risk score.

        Accepts a dict with optional keys:
        - severity: str  (none/low/moderate/high/severe/extreme)
        - wind_speed_kmh: float
        - visibility_km: float
        - score: float  (pre-computed override)
        """
        if "score" in weather_data:
            return _clamp(float(weather_data["score"]))

        severity_label = str(weather_data.get("severity", "none")).lower()
        base = self._SEVERITY_MAP.get(severity_label, 0.0)

        # Adjust for wind speed
        wind = float(weather_data.get("wind_speed_kmh", 0))
        if wind > 120:
            base = max(base, 70.0)
        elif wind > 80:
            base = max(base, 40.0)

        # Adjust for visibility
        vis = weather_data.get("visibility_km")
        if vis is not None:
            vis = float(vis)
            if vis < 0.5:
                base = max(base, 60.0)
            elif vis < 2.0:
                base = max(base, 30.0)

        return _clamp(base)


class OperationalRiskEvaluator:
    """Scores operational risk from carrier performance and node dwell time (0–100)."""

    def evaluate(
        self,
        carrier_score: float,
        dwell_time: float,
        p90_dwell: float,
    ) -> float:
        """
        Returns 0–100.

        - carrier_score: carrier risk score (0–100, higher = riskier)
        - dwell_time: current node dwell time in hours
        - p90_dwell: 90th-percentile baseline dwell time in hours

        Flags a bottleneck when dwell_time > p90_dwell.
        """
        score = _clamp(carrier_score) * 0.6

        if p90_dwell > 0 and dwell_time > p90_dwell:
            # Bottleneck: scale excess dwell into additional risk
            excess_ratio = min((dwell_time - p90_dwell) / p90_dwell, 1.0)
            score += excess_ratio * 40.0

        return _clamp(score)


class WarStateEvaluator:
    """Maps War_State classification to a risk score (0–100)."""

    _STATE_SCORES: dict[str, float] = {
        "Safe": 0.0,
        "Caution": 20.0,
        "High_Risk": 50.0,
        "Restricted": 80.0,
    }
    _MINIMUM_HIGH_RISK = 30.0

    def evaluate(self, war_state: str) -> float:
        """
        Returns the base score for the given war state.
        High_Risk and Restricted states add a minimum of 30 points.
        """
        base = self._STATE_SCORES.get(war_state, 0.0)
        if war_state in ("High_Risk", "Restricted"):
            base = max(base, self._MINIMUM_HIGH_RISK)
        return _clamp(base)


class GeopoliticalRiskEvaluator:
    """Returns the Geopolitical_Risk_Index directly (0–100)."""

    def evaluate(self, geopolitical_risk_index: float) -> float:
        return _clamp(geopolitical_risk_index)
