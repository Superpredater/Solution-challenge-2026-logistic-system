"""Data Ingestion Pipeline — FastAPI app with RestPoller startup."""

from __future__ import annotations

import asyncio
import logging
import os

import uvicorn
from fastapi import FastAPI

from .rest_poller import RestPoller
from .webhook_receiver import router as webhook_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Data Ingestion Service", version="1.0.0")
app.include_router(webhook_router)

# Default polling sources — override via environment / config in production
DEFAULT_SOURCES: list[dict] = [
    {
        "url": os.getenv("WEATHER_API_URL", "http://weather-api/events"),
        "source_type": "rest",
        "event_type": "weather_update",
        "interval_seconds": int(os.getenv("WEATHER_POLL_INTERVAL", "60")),
        "headers": {},
    },
    {
        "url": os.getenv("CARRIER_API_URL", "http://carrier-api/updates"),
        "source_type": "rest",
        "event_type": "carrier_update",
        "interval_seconds": int(os.getenv("CARRIER_POLL_INTERVAL", "30")),
        "headers": {},
    },
    {
        "url": os.getenv("PORT_API_URL", "http://port-api/events"),
        "source_type": "rest",
        "event_type": "port_event",
        "interval_seconds": int(os.getenv("PORT_POLL_INTERVAL", "60")),
        "headers": {},
    },
]


@app.on_event("startup")
async def startup_event() -> None:
    poller = RestPoller(DEFAULT_SOURCES)
    asyncio.create_task(poller.start())
    logger.info("RestPoller started with %d sources", len(DEFAULT_SOURCES))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "data-ingestion"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("services.data-ingestion.main:app", host="0.0.0.0", port=8011, reload=False)
