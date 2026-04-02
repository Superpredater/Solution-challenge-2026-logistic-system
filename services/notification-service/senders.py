"""Email, SMS, and webhook delivery stubs with retry logic."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging

import httpx

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [30, 60, 120]


async def _retry_post(
    client: httpx.AsyncClient,
    url: str,
    **kwargs,
) -> httpx.Response | None:
    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        try:
            resp = await client.post(url, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            logger.warning("Attempt %d failed: %s", attempt, exc)
            if attempt < len(_RETRY_DELAYS):
                await asyncio.sleep(delay)
    return None


class EmailSender:
    """Send email via SendGrid API (stub)."""

    SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def send(self, to: str, subject: str, body: str) -> bool:
        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": "noreply@supplychain.example"},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await _retry_post(
                client,
                self.SENDGRID_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        return resp is not None


class SMSSender:
    """Send SMS via Twilio API (stub)."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number

    async def send(self, to: str, body: str) -> bool:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._account_sid}/Messages.json"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await _retry_post(
                client,
                url,
                data={"To": to, "From": self._from_number, "Body": body},
                auth=(self._account_sid, self._auth_token),
            )
        return resp is not None


class WebhookDispatcher:
    """HTTP POST with HMAC-SHA256 signature header."""

    async def send(self, url: str, payload: dict, secret: str) -> bool:
        body = json.dumps(payload, default=str).encode()
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await _retry_post(
                client,
                url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature-SHA256": sig,
                },
            )
        return resp is not None
