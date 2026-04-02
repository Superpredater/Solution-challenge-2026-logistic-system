"""AI Service — Kafka consumer + FastAPI chat and report endpoints."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.shared.config import settings
from services.shared.kafka import consume
from .anomaly_explainer import AnomalyExplainer
from .chatbot_handler import ChatbotHandler
from .fallback_explainer import FallbackExplainer
from .gemini_client import GeminiClient
from .narrative_report_generator import NarrativeReportGenerator
from .news_event_summarizer import NewsEventSummarizer
from .risk_explainer import RiskExplainer

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Service", version="1.0.0")

_gemini = GeminiClient(timeout=5.0)  # picks up GEMINI_API_KEY from env
_fallback = FallbackExplainer()
_risk_explainer = RiskExplainer()
_news_summarizer = NewsEventSummarizer()
_anomaly_explainer = AnomalyExplainer()
_narrative_gen = NarrativeReportGenerator()


# ------------------------------------------------------------------
# Kafka consumer
# ------------------------------------------------------------------

async def _handle_message(topic: str, value: dict[str, Any]) -> None:
    if topic == "risk.score.updates":
        shipment_id = value.get("shipment_id")
        risk_score = value.get("risk_score", 0.0)
        if risk_score > 50 and shipment_id:
            explanation = await _risk_explainer.explain(
                UUID(shipment_id), risk_score, value, _gemini, _fallback
            )
            logger.info("Risk explanation for %s: %s", shipment_id, explanation[:80])
    elif topic == "raw.news.events":
        summary = await _news_summarizer.summarize(value, _gemini, _fallback)
        logger.info("News summary: %s", summary[:80])
    elif topic == "anomaly.detected":
        shipment_id = value.get("shipment_id")
        patterns = value.get("patterns", [])
        if shipment_id:
            explanation = await _anomaly_explainer.explain(
                UUID(shipment_id), patterns, _gemini, _fallback
            )
            logger.info("Anomaly explanation for %s: %s", shipment_id, explanation[:80])


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(
        consume(
            ["risk.score.updates", "raw.news.events", "anomaly.detected"],
            "ai-service",
            _handle_message,
        )
    )


# ------------------------------------------------------------------
# REST endpoints
# ------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str
    message: str
    context: dict = {}


class ChatResponse(BaseModel):
    response: str
    session_id: str
    fallback_used: bool = False


@app.post("/api/v1/ai/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(settings.redis_url)
        handler = ChatbotHandler(redis_client)
        response = await handler.handle(req.session_id, req.message, req.context, _gemini)
        return ChatResponse(
            response=response,
            session_id=req.session_id,
            fallback_used=not _gemini.is_available(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class NarrativeReportRequest(BaseModel):
    tenant_id: UUID
    summary_data: dict


@app.post("/api/v1/ai/reports/narrative")
async def narrative_report(req: NarrativeReportRequest) -> dict:
    report = await _narrative_gen.generate(
        req.tenant_id, req.summary_data, _gemini, _fallback
    )
    return {"tenant_id": str(req.tenant_id), "report": report}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "gemini_available": _gemini.is_available()}
