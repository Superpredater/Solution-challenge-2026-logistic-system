"""Summarize geopolitical news events via Gemini or fallback."""

from __future__ import annotations

from .fallback_explainer import FallbackExplainer
from .gemini_client import GeminiClient


class NewsEventSummarizer:
    """Generate concise news summaries with supply chain impact."""

    async def summarize(
        self,
        event: dict,
        client: GeminiClient,
        fallback: FallbackExplainer,
    ) -> str:
        event_type = event.get("event_type", "unknown")
        region = event.get("region", "unknown region")
        description = event.get("description", "")

        prompt = (
            f"Summarize this supply chain news event in 2-3 sentences and describe "
            f"the projected impact: type={event_type}, region={region}, "
            f"details={description}"
        )
        try:
            return await client.generate(prompt)
        except Exception:
            return fallback.summarize_news(event_type, region)
