"""Demand forecasting using a simple moving average stub."""

from __future__ import annotations

from uuid import UUID


class DemandForecaster:
    """Forecast 7-day demand per geographic zone."""

    _THRESHOLD = 1000.0  # units — configurable in production

    def forecast(self, zone_id: UUID, historical_data: list[dict]) -> dict:
        """Return 7-day demand forecast using a simple moving average."""
        if not historical_data:
            return {
                "zone_id": zone_id,
                "forecast_7d": [0.0] * 7,
                "peak_day": 0,
                "exceeds_threshold": False,
            }

        values = [float(d.get("demand", 0.0)) for d in historical_data]
        window = min(len(values), 7)
        avg = sum(values[-window:]) / window

        # Simple projection: slight linear trend from last value
        last = values[-1] if values else avg
        trend = (last - values[0]) / max(len(values) - 1, 1) if len(values) > 1 else 0.0

        forecast_7d = [max(avg + trend * i, 0.0) for i in range(7)]
        peak_day = int(max(range(7), key=lambda i: forecast_7d[i]))
        exceeds_threshold = any(v > self._THRESHOLD for v in forecast_7d)

        return {
            "zone_id": zone_id,
            "forecast_7d": forecast_7d,
            "peak_day": peak_day,
            "exceeds_threshold": exceeds_threshold,
        }
