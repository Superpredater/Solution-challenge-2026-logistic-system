"""Collaboration Workspace — WebSocket handler for real-time messaging."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.shared.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/collaboration/{shipment_id}")
async def collaboration_websocket(websocket: WebSocket, shipment_id: str) -> None:
    """Subscribe to Redis pub/sub and forward messages to the connected client."""
    await websocket.accept()
    channel = f"collab:{shipment_id}"
    logger.info("WebSocket client connected to channel %s", channel)

    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                try:
                    await websocket.send_text(data)
                except WebSocketDisconnect:
                    break
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from channel %s", channel)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await redis.aclose()
        logger.info("WebSocket handler cleaned up for channel %s", channel)
