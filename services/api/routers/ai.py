"""REST API — /api/v1/ai router (chatbot and narrative reports)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth_service.rbac import require_permission
from services.shared.database import AsyncSessionLocal

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/chat")
async def chat(
    body: dict[str, Any],
    principal=Depends(require_permission("ai:query")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Chatbot endpoint — delegates to AI service."""
    from services.ai_service.chatbot_handler import ChatbotHandler

    start = time.monotonic()
    handler = ChatbotHandler()
    session_id = body.get("session_id", "")
    message = body.get("message", "")
    _, tenant_id, stakeholder_id = principal

    result = await handler.handle(
        session_id=session_id,
        message=message,
        tenant_id=tenant_id,
        stakeholder_id=stakeholder_id,
        db_session=session,
    )
    latency_ms = (time.monotonic() - start) * 1000
    return {
        "response": result.get("response", ""),
        "session_id": session_id,
        "latency_ms": round(latency_ms, 1),
        "fallback_used": result.get("fallback_used", False),
    }


@router.post("/reports/narrative")
async def generate_narrative_report(
    body: dict[str, Any],
    principal=Depends(require_permission("reports:generate")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Generate a narrative report via AI service."""
    from services.ai_service.narrative_report_generator import NarrativeReportGenerator

    _, tenant_id, _ = principal
    generator = NarrativeReportGenerator()
    report = await generator.generate(
        tenant_id=tenant_id,
        context=body.get("context", {}),
        db_session=session,
    )
    return {"report": report}
