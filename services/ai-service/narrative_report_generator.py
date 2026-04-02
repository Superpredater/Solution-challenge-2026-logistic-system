"""Generate narrative supply chain performance reports."""

from __future__ import annotations

from uuid import UUID

from .fallback_explainer import FallbackExplainer
from .gemini_client import GeminiClient


class NarrativeReportGenerator:
    """Generate automated narrative reports for tenants."""

    async def generate(
        self,
        tenant_id: UUID,
        summary_data: dict,
        client: GeminiClient,
        fallback: FallbackExplainer,
    ) -> str:
        prompt = (
            f"Generate a professional supply chain performance narrative report for "
            f"tenant {tenant_id}. Data: {summary_data}. "
            "Include: disruption trends, risk outlook, and top recommendations. "
            "Keep it under 300 words."
        )
        try:
            return await client.generate(prompt)
        except Exception:
            return (
                f"Supply chain report for tenant {tenant_id}. "
                f"Summary: {summary_data}. AI narrative unavailable — using template."
            )
