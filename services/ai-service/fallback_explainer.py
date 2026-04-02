"""Template-based fallback explainer for when Gemini is unavailable."""

from __future__ import annotations

import asyncio
import logging

from services.shared.kafka import publish

logger = logging.getLogger(__name__)

_DEGRADED_TOPIC = "system.degraded_mode.events"


class FallbackExplainer:
    """Generate rule-based explanations without Gemini."""

    def explain_risk(self, risk_score: float, components: dict) -> str:
        parts = []
        if components.get("weather_component", 0) > 30:
            parts.append("severe weather conditions")
        if components.get("war_state_component", 0) > 30:
            parts.append("active conflict zones on the route")
        if components.get("operational_component", 0) > 30:
            parts.append("carrier operational delays")
        if components.get("geopolitical_component", 0) > 30:
            parts.append("elevated geopolitical risk")
        reason = ", ".join(parts) if parts else "multiple risk factors"
        self._log_degraded("risk_explanation")
        return (
            f"Risk score of {risk_score:.1f} is driven by {reason}. "
            "Manual review is recommended."
        )

    def explain_anomaly(self, patterns: list[str]) -> str:
        self._log_degraded("anomaly_explanation")
        if not patterns:
            return "No anomalous patterns detected."
        pattern_str = ", ".join(patterns)
        return (
            f"Anomalous behaviour detected: {pattern_str}. "
            "Immediate investigation is advised."
        )

    def summarize_news(self, event_type: str, region: str) -> str:
        self._log_degraded("news_summary")
        return (
            f"A {event_type} event has been reported in {region}. "
            "Supply chain impact assessment is pending."
        )

    def _log_degraded(self, interaction_type: str) -> None:
        asyncio.create_task(
            publish(
                _DEGRADED_TOPIC,
                {"event": "fallback_used", "interaction_type": interaction_type},
            )
        )
