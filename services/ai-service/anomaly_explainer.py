"""Explain detected anomaly patterns via Gemini or fallback."""

from __future__ import annotations

from uuid import UUID

from .fallback_explainer import FallbackExplainer
from .gemini_client import GeminiClient


class AnomalyExplainer:
    """Generate anomaly explanations and suggested response actions."""

    async def explain(
        self,
        shipment_id: UUID,
        patterns: list[str],
        client: GeminiClient,
        fallback: FallbackExplainer,
    ) -> str:
        prompt = (
            f"Shipment {shipment_id} has triggered anomaly detection with patterns: "
            f"{patterns}. Explain what this likely means and suggest 2-3 response actions."
        )
        try:
            return await client.generate(prompt)
        except Exception:
            return fallback.explain_anomaly(patterns)
