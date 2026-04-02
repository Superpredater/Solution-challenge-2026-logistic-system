"""Classify alert severity from risk score and trigger type."""

from __future__ import annotations

_ALWAYS_CRITICAL = {"war_state_change", "geopolitical_spike"}


class AlertClassifier:
    """Assign Informational / Warning / Critical severity."""

    def classify(self, risk_score: float, trigger_type: str) -> str:
        if trigger_type in _ALWAYS_CRITICAL:
            return "Critical"
        if risk_score >= 70:
            return "Critical"
        if risk_score >= 40:
            return "Warning"
        return "Informational"
