"""Gemini API client with circuit breaker and retry logic."""

from __future__ import annotations

import asyncio
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

# Default key from environment — can be overridden per-instance
_DEFAULT_API_KEY = os.environ.get("GEMINI_API_KEY", "")

_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
_MAX_FAILURES = 3
_HALF_OPEN_SECONDS = 60.0


class GeminiClient:
    """Async Gemini API wrapper with circuit breaker."""

    def __init__(self, api_key: str = "", timeout: float = 5.0) -> None:
        self._api_key = api_key or _DEFAULT_API_KEY
        self._timeout = timeout
        self._failures = 0
        self._opened_at: float | None = None

    # ------------------------------------------------------------------
    # Circuit breaker state
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        if self._failures < _MAX_FAILURES:
            return True
        if self._opened_at and (time.monotonic() - self._opened_at) >= _HALF_OPEN_SECONDS:
            # Half-open: allow one probe
            return True
        return False

    def _record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def _record_failure(self) -> None:
        self._failures += 1
        if self._failures >= _MAX_FAILURES:
            self._opened_at = time.monotonic()

    # ------------------------------------------------------------------
    # API call
    # ------------------------------------------------------------------

    async def generate(self, prompt: str) -> str:
        if not self.is_available():
            raise RuntimeError("GeminiClient circuit breaker is open")

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        last_exc: Exception | None = None

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{_GEMINI_URL}?key={self._api_key}",
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    self._record_success()
                    return text
            except Exception as exc:
                last_exc = exc
                logger.warning("Gemini attempt %d failed: %s", attempt + 1, exc)
                if attempt < 2:
                    await asyncio.sleep(1.0 * (attempt + 1))

        self._record_failure()
        raise RuntimeError(f"Gemini API unavailable after 3 attempts: {last_exc}") from last_exc
