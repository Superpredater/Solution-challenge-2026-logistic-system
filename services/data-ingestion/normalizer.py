"""Normalizes source-specific payloads into canonical InternalEvent dict format."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class Normalizer:
    """Transforms carrier, weather, port, news, and GPS payloads into InternalEvent dicts."""

    def normalize(
        self,
        raw: dict[str, Any],
        source_type: str,
        event_type: str,
    ) -> dict[str, Any]:
        """Return a dict conforming to the InternalEvent schema."""
        handler = self._handlers.get(event_type, self._generic)
        return handler(raw, source_type, event_type)

    # ------------------------------------------------------------------
    # Source-specific handlers
    # ------------------------------------------------------------------

    def _weather(self, raw: dict[str, Any], source_type: str, event_type: str) -> dict[str, Any]:
        return {
            "event_id": str(raw.get("id", uuid4())),
            "source_type": source_type,
            "event_type": event_type,
            "payload": {
                "condition": raw.get("condition") or raw.get("weather_condition"),
                "severity": raw.get("severity") or raw.get("alert_level"),
                "location": raw.get("location") or raw.get("geo"),
                "wind_speed_kmh": raw.get("wind_speed_kmh") or raw.get("wind"),
                "visibility_km": raw.get("visibility_km") or raw.get("visibility"),
            },
            "region_id": raw.get("region_id"),
            "node_ids": raw.get("node_ids", []),
            "timestamp": self._ts(raw),
            "raw_source": raw.get("source", "weather_api"),
        }

    def _carrier(self, raw: dict[str, Any], source_type: str, event_type: str) -> dict[str, Any]:
        return {
            "event_id": str(raw.get("event_id") or raw.get("id", uuid4())),
            "source_type": source_type,
            "event_type": event_type,
            "payload": {
                "carrier_id": raw.get("carrier_id") or raw.get("carrierId"),
                "shipment_id": raw.get("shipment_id") or raw.get("shipmentId"),
                "delay_minutes": raw.get("delay_minutes") or raw.get("delayMinutes", 0),
                "status": raw.get("status") or raw.get("delivery_status"),
                "reason": raw.get("reason") or raw.get("delay_reason"),
            },
            "region_id": raw.get("region_id"),
            "node_ids": raw.get("node_ids", []),
            "timestamp": self._ts(raw),
            "raw_source": raw.get("source", "carrier_api"),
        }

    def _port(self, raw: dict[str, Any], source_type: str, event_type: str) -> dict[str, Any]:
        return {
            "event_id": str(raw.get("event_id") or raw.get("id", uuid4())),
            "source_type": source_type,
            "event_type": event_type,
            "payload": {
                "port_id": raw.get("port_id") or raw.get("portId"),
                "event_subtype": raw.get("event_subtype") or raw.get("type"),
                "congestion_level": raw.get("congestion_level") or raw.get("congestion"),
                "closure_reason": raw.get("closure_reason"),
                "estimated_reopening": raw.get("estimated_reopening"),
            },
            "region_id": raw.get("region_id"),
            "node_ids": raw.get("node_ids", []),
            "timestamp": self._ts(raw),
            "raw_source": raw.get("source", "port_authority"),
        }

    def _news(self, raw: dict[str, Any], source_type: str, event_type: str) -> dict[str, Any]:
        return {
            "event_id": str(raw.get("article_id") or raw.get("id", uuid4())),
            "source_type": source_type,
            "event_type": event_type,
            "payload": {
                "title": raw.get("title") or raw.get("headline"),
                "body": raw.get("body") or raw.get("content") or raw.get("text"),
                "language": raw.get("language", "en"),
                "url": raw.get("url"),
                "published_at": raw.get("published_at") or raw.get("publishedAt"),
            },
            "region_id": raw.get("region_id"),
            "node_ids": raw.get("node_ids", []),
            "timestamp": self._ts(raw),
            "raw_source": raw.get("source", "news_feed"),
        }

    def _gps(self, raw: dict[str, Any], source_type: str, event_type: str) -> dict[str, Any]:
        return {
            "event_id": str(raw.get("fix_id") or raw.get("id", uuid4())),
            "source_type": source_type,
            "event_type": event_type,
            "payload": {
                "shipment_id": raw.get("shipment_id") or raw.get("shipmentId"),
                "latitude": raw.get("latitude") or raw.get("lat"),
                "longitude": raw.get("longitude") or raw.get("lon") or raw.get("lng"),
                "speed_kmh": raw.get("speed_kmh") or raw.get("speed"),
                "heading": raw.get("heading"),
            },
            "region_id": raw.get("region_id"),
            "node_ids": raw.get("node_ids", []),
            "timestamp": self._ts(raw),
            "raw_source": raw.get("source", "gps_device"),
        }

    def _generic(self, raw: dict[str, Any], source_type: str, event_type: str) -> dict[str, Any]:
        return {
            "event_id": str(raw.get("event_id") or raw.get("id", uuid4())),
            "source_type": source_type,
            "event_type": event_type,
            "payload": raw,
            "region_id": raw.get("region_id"),
            "node_ids": raw.get("node_ids", []),
            "timestamp": self._ts(raw),
            "raw_source": raw.get("source", source_type),
        }

    @property
    def _handlers(self):
        return {
            "weather_update": self._weather,
            "carrier_update": self._carrier,
            "port_event": self._port,
            "news_event": self._news,
            "shipment_position": self._gps,
        }

    @staticmethod
    def _ts(raw: dict[str, Any]) -> str:
        ts = raw.get("timestamp") or raw.get("ts") or raw.get("event_time")
        if ts:
            return ts if isinstance(ts, str) else str(ts)
        return datetime.now(timezone.utc).isoformat()
