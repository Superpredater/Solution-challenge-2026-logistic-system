"""Edge Agent — main loop: collect GPS events, buffer, heartbeat, sync on reconnect."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import aiohttp

from .local_buffer import LocalBuffer
from .local_rule_engine import LocalRuleEngine
from .sync_manager import SyncManager

logger = logging.getLogger(__name__)

CENTRAL_API_URL = os.environ.get("CENTRAL_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("EDGE_API_KEY", "dev-edge-key")
AGENT_ID = os.environ.get("EDGE_AGENT_ID", "edge-agent-001")
HEARTBEAT_INTERVAL = 60  # seconds
RULES_PATH = os.environ.get("RULES_PATH", "cached_rules.json")
DB_PATH = os.environ.get("EDGE_DB_PATH", "edge_buffer.db")


def _collect_gps_event() -> dict[str, Any] | None:
    """Collect a GPS/IoT event from local hardware.

    In production this reads from a serial port or local sensor API.
    Returns None when no new event is available.
    """
    # Stub: in production, read from hardware interface
    return None


async def _send_heartbeat(api_base_url: str, api_key: str, agent_id: str) -> bool:
    """Send a heartbeat to the central system. Returns True on success."""
    url = f"{api_base_url.rstrip('/')}/api/v1/edge/heartbeat"
    headers = {"X-API-Key": api_key}
    payload = {
        "agent_id": agent_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
    except Exception as exc:
        logger.debug("Heartbeat failed: %s", exc)
        return False


async def main_loop() -> None:
    """Main edge agent loop."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Edge Agent %s starting (API: %s)", AGENT_ID, CENTRAL_API_URL)

    buffer = LocalBuffer(db_path=DB_PATH)
    rule_engine = LocalRuleEngine()
    rule_engine.load_rules(RULES_PATH)
    sync_manager = SyncManager()

    last_heartbeat = 0.0

    while True:
        now = time.monotonic()

        # Collect GPS/IoT event and buffer it
        event = _collect_gps_event()
        if event is not None:
            recorded_at = datetime.now(timezone.utc).isoformat()
            buffer.add_event(event, recorded_at)
            logger.debug("Buffered event: %s", event)

        # Heartbeat + sync every 60 seconds
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            online = await _send_heartbeat(CENTRAL_API_URL, API_KEY, AGENT_ID)
            if online:
                logger.info("Heartbeat OK — syncing buffered events")
                await sync_manager.sync(CENTRAL_API_URL, API_KEY, buffer)
            else:
                logger.info("Offline — events buffered locally")
            last_heartbeat = now

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main_loop())
