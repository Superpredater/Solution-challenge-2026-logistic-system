"""Edge Agent — LocalRuleEngine: applies cached rules for offline operation."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class LocalRuleEngine:
    """Applies cached routing and risk rules during offline periods (Req 19.3)."""

    def __init__(self) -> None:
        self._rules: dict[str, Any] = {}

    def load_rules(self, rules_path: str = "cached_rules.json") -> None:
        """Load JSON rules file from disk."""
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                self._rules = json.load(f)
            logger.info("Loaded rules from %s", rules_path)
        except FileNotFoundError:
            logger.warning("Rules file not found at %s; using empty ruleset", rules_path)
            self._rules = {}
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse rules file %s: %s", rules_path, exc)
            self._rules = {}

    def evaluate_risk(self, shipment_data: dict[str, Any]) -> float:
        """Apply cached risk rules and return a risk score (0–100)."""
        risk_rules: list[dict[str, Any]] = self._rules.get("risk_rules", [])
        score = 0.0

        for rule in risk_rules:
            field = rule.get("field", "")
            operator = rule.get("operator", "eq")
            value = rule.get("value")
            weight = float(rule.get("weight", 0.0))

            actual = shipment_data.get(field)
            if actual is None:
                continue

            matched = False
            if operator == "eq":
                matched = actual == value
            elif operator == "gt":
                matched = float(actual) > float(value)
            elif operator == "lt":
                matched = float(actual) < float(value)
            elif operator == "gte":
                matched = float(actual) >= float(value)
            elif operator == "lte":
                matched = float(actual) <= float(value)
            elif operator == "in":
                matched = actual in (value or [])

            if matched:
                score += weight

        return min(max(score, 0.0), 100.0)

    def get_route(self, origin_id: str, destination_id: str) -> list[str]:
        """Return cached route node IDs for the given origin→destination pair."""
        routes: dict[str, Any] = self._rules.get("routes", {})
        key = f"{origin_id}:{destination_id}"
        route = routes.get(key, [])
        if not route:
            logger.debug("No cached route for %s → %s", origin_id, destination_id)
        return route
