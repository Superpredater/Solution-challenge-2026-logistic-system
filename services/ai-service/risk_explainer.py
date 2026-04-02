"""Generate natural language risk explanations via Gemini or fallback."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.models import AIInteractionLog
from .ai_interaction_logger import AIInteractionLogger
from .fallback_explainer import FallbackExplainer
from .gemini_client import GeminiClient

_logger_svc = AIInteractionLogger()


class RiskExplainer:
    """Explain risk scores using Gemini with fallback."""

    async def explain(
        self,
        shipment_id: UUID,
        risk_score: float,
        components: dict,
        client: GeminiClient,
        fallback: FallbackExplainer,
        session: AsyncSession | None = None,
        tenant_id: UUID | None = None,
        stakeholder_id: UUID | None = None,
    ) -> str:
        prompt = (
            f"Explain in 2-3 sentences why shipment {shipment_id} has a risk score of "
            f"{risk_score:.1f}/100. Contributing factors: {components}. "
            "Be concise and actionable."
        )
        start = time.monotonic()
        fallback_used = False
        try:
            response = await client.generate(prompt)
            model_used = "gemini-1.5-pro"
        except Exception:
            response = fallback.explain_risk(risk_score, components)
            model_used = "fallback"
            fallback_used = True

        latency_ms = int((time.monotonic() - start) * 1000)

        if session and tenant_id and stakeholder_id:
            log = AIInteractionLog(
                interaction_id=uuid.uuid4(),
                tenant_id=tenant_id,
                stakeholder_id=stakeholder_id,
                interaction_type="risk_explanation",
                query=prompt,
                response=response,
                model_used=model_used,
                latency_ms=latency_ms,
                fallback_used=fallback_used,
                timestamp=datetime.now(timezone.utc),
            )
            await _logger_svc.log(log, session)

        return response
