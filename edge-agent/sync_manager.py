"""Edge Agent — SyncManager: uploads buffered events to the central system."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from .local_buffer import LocalBuffer

logger = logging.getLogger(__name__)

SYNC_TIMEOUT_SECONDS = 60
BATCH_SIZE = 500


class SyncManager:
    """Uploads unsynced events to the central API on reconnection (Req 19.2)."""

    async def sync(
        self,
        api_base_url: str,
        api_key: str,
        buffer: LocalBuffer,
    ) -> None:
        """Upload all unsynced events in batches of 500.

        Completes within 60 seconds total.
        """
        start = time.monotonic()
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        endpoint = f"{api_base_url.rstrip('/')}/api/v1/edge/sync"

        async with aiohttp.ClientSession(headers=headers) as http:
            while True:
                elapsed = time.monotonic() - start
                if elapsed >= SYNC_TIMEOUT_SECONDS:
                    logger.warning("Sync timeout reached after %.1fs", elapsed)
                    break

                events = buffer.get_unsynced_events(limit=BATCH_SIZE)
                if not events:
                    logger.info("All events synced")
                    break

                remaining = SYNC_TIMEOUT_SECONDS - elapsed
                try:
                    async with http.post(
                        endpoint,
                        json={"events": events},
                        timeout=aiohttp.ClientTimeout(total=min(30.0, remaining)),
                    ) as resp:
                        if resp.status == 200:
                            ids = [e["id"] for e in events]
                            buffer.mark_synced(ids)
                            logger.info("Synced batch of %d events", len(ids))
                        else:
                            body = await resp.text()
                            logger.warning(
                                "Sync batch failed: HTTP %d — %s", resp.status, body[:200]
                            )
                            break
                except asyncio.TimeoutError:
                    logger.warning("Sync batch timed out")
                    break
                except aiohttp.ClientError as exc:
                    logger.warning("Sync batch error: %s", exc)
                    break
