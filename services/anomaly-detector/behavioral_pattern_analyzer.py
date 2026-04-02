"""Rule-based behavioral pattern analysis for fraud/theft detection."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

_UNEXPECTED_STOP_HOURS = 4.0
_ABNORMAL_DWELL_MULTIPLIER = 2.0


class BehavioralPatternAnalyzer:
    """Detect suspicious shipment behaviour from event streams."""

    def analyze(self, shipment_id: UUID, events: list[dict]) -> dict:
        patterns: list[str] = []

        # Detect unexpected stops (dwell > 4h at non-node location)
        for event in events:
            if event.get("type") == "position_update":
                dwell_h = event.get("dwell_hours", 0.0)
                is_node = event.get("at_node", False)
                if not is_node and dwell_h > _UNEXPECTED_STOP_HOURS:
                    patterns.append("unexpected_stop")
                    break

        # Detect unauthorized node visits
        for event in events:
            if event.get("type") == "node_visit" and not event.get("authorized", True):
                patterns.append("unauthorized_node_visit")
                break

        # Detect abnormal dwell time (> 2x p90)
        for event in events:
            if event.get("type") == "node_dwell":
                dwell_h = event.get("dwell_hours", 0.0)
                p90 = event.get("p90_dwell_hours", 0.0)
                if p90 > 0 and dwell_h > _ABNORMAL_DWELL_MULTIPLIER * p90:
                    patterns.append("abnormal_dwell_time")
                    break

        is_suspicious = len(patterns) > 0
        confidence = min(0.3 * len(patterns), 1.0)

        return {
            "is_suspicious": is_suspicious,
            "patterns": patterns,
            "confidence": confidence,
        }
