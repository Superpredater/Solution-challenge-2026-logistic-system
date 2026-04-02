"""Suppress non-critical alerts during tenant quiet periods."""

from __future__ import annotations

from datetime import datetime, timezone

from services.shared.models import Tenant


class QuietPeriodEnforcer:
    """Return True if the alert should be suppressed."""

    def should_suppress(self, tenant: Tenant, severity: str) -> bool:
        if severity == "Critical":
            return False
        if tenant.quiet_period_start is None or tenant.quiet_period_end is None:
            return False
        now_time = datetime.now(timezone.utc).time().replace(tzinfo=None)
        start = tenant.quiet_period_start
        end = tenant.quiet_period_end
        if start <= end:
            return start <= now_time <= end
        # Overnight window (e.g. 22:00 – 06:00)
        return now_time >= start or now_time <= end
