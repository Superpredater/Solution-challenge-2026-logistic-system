"""War state classifier — maps geopolitical signals to Safe/Caution/High_Risk/Restricted."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.kafka import publish
from .region_registry import RegionRegistry

logger = logging.getLogger(__name__)

WAR_STATE_TOPIC = "war.state.updates"

# State ordering for escalation logic
_STATE_ORDER = ["Safe", "Caution", "High_Risk", "Restricted"]


class WarStateClassifier:
    """Classifies a region's war state from extracted geopolitical signals."""

    def __init__(self) -> None:
        self._registry = RegionRegistry()

    def classify(self, signals: dict, current_state: str) -> str:
        """
        Returns the new war state based on signal combination.

        Rules (highest matching wins):
        - Restricted: conflict=True AND (airspace closure OR naval blockade)
        - High_Risk:  conflict=True
        - Caution:    instability=True OR sanctions=True OR trade_restrictions=True
        - Safe:       no significant signals
        """
        conflict: bool = signals.get("conflict", False)
        instability: bool = signals.get("instability", False)
        sanctions: bool = signals.get("sanctions", False)
        trade_restrictions: bool = signals.get("trade_restrictions", False)
        airspace_closure: bool = signals.get("airspace_closure", False)
        naval_blockade: bool = signals.get("naval_blockade", False)

        if conflict and (airspace_closure or naval_blockade):
            new_state = "Restricted"
        elif conflict:
            new_state = "High_Risk"
        elif instability or sanctions or trade_restrictions:
            new_state = "Caution"
        else:
            new_state = "Safe"

        # Never downgrade more than one level per evaluation
        current_idx = _STATE_ORDER.index(current_state) if current_state in _STATE_ORDER else 0
        new_idx = _STATE_ORDER.index(new_state)
        if new_idx < current_idx - 1:
            new_state = _STATE_ORDER[current_idx - 1]

        return new_state

    async def update_region_war_state(
        self, region_id: UUID, new_state: str, session: AsyncSession
    ) -> None:
        """Persist the new war state and publish to war.state.updates."""
        await self._registry.update_war_state(region_id, new_state, session)
        await publish(
            WAR_STATE_TOPIC,
            {
                "event": "war_state_update",
                "region_id": str(region_id),
                "new_state": new_state,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info("Region %s war state → %s", region_id, new_state)
