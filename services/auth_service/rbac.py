"""Role-Based Access Control — permission matrix and FastAPI dependencies."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth_service import verify_token

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Permission matrix (each role inherits all lower-role permissions)
# ---------------------------------------------------------------------------

_VIEWER_PERMISSIONS: set[str] = {
    "shipments:read",
    "routes:read",
    "alerts:read",
    "regions:read",
    "carriers:read",
    "reports:read",
}

_ANALYST_PERMISSIONS: set[str] = _VIEWER_PERMISSIONS | {
    "reports:generate",
    "ai:query",
    "analytics:read",
}

_MANAGER_PERMISSIONS: set[str] = _ANALYST_PERMISSIONS | {
    "recommendations:approve",
    "recommendations:reject",
    "decisions:override",
    "collaboration:write",
    "scenarios:run",
}

_ADMIN_PERMISSIONS: set[str] = _MANAGER_PERMISSIONS | {
    "admin:manage",
    "tenants:configure",
    "stakeholders:manage",
    "audit:read",
    "autonomous:configure",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "Viewer": _VIEWER_PERMISSIONS,
    "Analyst": _ANALYST_PERMISSIONS,
    "Manager": _MANAGER_PERMISSIONS,
    "Admin": _ADMIN_PERMISSIONS,
}


def check_permission(role: str, required_permission: str) -> bool:
    """Return True if the given role has the required permission."""
    return required_permission in ROLE_PERMISSIONS.get(role, set())


# ---------------------------------------------------------------------------
# FastAPI security scheme
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=True)


async def get_current_stakeholder(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Tuple[str, str, str]:
    """Extract and verify JWT; return (stakeholder_id, tenant_id, role)."""
    payload = verify_token(credentials.credentials)
    stakeholder_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role = payload.get("role")

    if not stakeholder_id or not tenant_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload",
        )
    return stakeholder_id, tenant_id, role


def require_permission(permission: str) -> Callable:
    """Return a FastAPI dependency that enforces a specific permission."""

    async def _dependency(
        principal: Tuple[str, str, str] = Depends(get_current_stakeholder),
    ) -> Tuple[str, str, str]:
        stakeholder_id, tenant_id, role = principal
        if not check_permission(role, permission):
            _log_denial(stakeholder_id, tenant_id, role, permission)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' required",
            )
        return principal

    return _dependency


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def _log_denial(stakeholder_id: str, tenant_id: str, role: str, permission: str) -> None:
    """Log a 403 denial to the security audit log."""
    entry = {
        "event": "permission_denied",
        "stakeholder_id": stakeholder_id,
        "tenant_id": tenant_id,
        "role": role,
        "required_permission": permission,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    # Emit to Kafka topic security.audit.events (best-effort; fire-and-forget)
    try:
        from services.shared.kafka import get_producer
        import asyncio

        async def _publish() -> None:
            producer = await get_producer()
            await producer.send("security.audit.events", value=entry)

        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_publish())
    except Exception:
        pass  # Never block the request on audit log failure

    logger.warning(
        "SECURITY_AUDIT permission_denied stakeholder=%s tenant=%s role=%s permission=%s",
        stakeholder_id,
        tenant_id,
        role,
        permission,
    )
