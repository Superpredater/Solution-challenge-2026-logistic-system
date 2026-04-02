"""Chatbot handler with Redis-backed conversation history."""

from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from .gemini_client import GeminiClient

logger = logging.getLogger(__name__)

_MAX_HISTORY = 10
_HISTORY_TTL = 3600  # 1 hour


class ChatbotHandler:
    """Handle chatbot messages with per-session conversation context."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    def _history_key(self, session_id: str) -> str:
        return f"chat:history:{session_id}"

    async def _load_history(self, session_id: str) -> list[dict]:
        raw = await self._redis.get(self._history_key(session_id))
        if raw:
            return json.loads(raw)
        return []

    async def _save_history(self, session_id: str, history: list[dict]) -> None:
        await self._redis.set(
            self._history_key(session_id),
            json.dumps(history[-_MAX_HISTORY:]),
            ex=_HISTORY_TTL,
        )

    async def handle(
        self,
        session_id: str,
        message: str,
        context: dict,
        client: GeminiClient,
    ) -> str:
        history = await self._load_history(session_id)

        context_str = ""
        if context:
            context_str = f"\n\nContext: {json.dumps(context, default=str)}"

        history_str = ""
        if history:
            history_str = "\n".join(
                f"{m['role'].capitalize()}: {m['content']}" for m in history
            )
            history_str = f"\n\nConversation history:\n{history_str}"

        prompt = (
            f"You are a supply chain intelligence assistant.{context_str}"
            f"{history_str}\n\nUser: {message}\nAssistant:"
        )

        try:
            response = await client.generate(prompt)
        except Exception as exc:
            logger.warning("Gemini unavailable for chatbot: %s", exc)
            response = "I'm currently unable to process your request. Please try again shortly."

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        await self._save_history(session_id, history)

        return response
