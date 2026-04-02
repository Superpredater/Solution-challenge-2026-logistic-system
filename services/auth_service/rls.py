"""Row-Level Security helpers and FastAPI middleware for tenant isolation."""

from __future__ import annotations

from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from services.shared.database import AsyncSessionLocal, set_rls_tenant

# Re-export for convenience
__all__ = ["set_rls_tenant", "get_tenant_db", "TenantRLSMiddleware"]


async def get_tenant_db(tenant_id: UUID) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a DB session with RLS set for tenant_id."""
    async with AsyncSessionLocal() as session:
        await set_rls_tenant(session, tenant_id)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class TenantRLSMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that extracts tenant_id from JWT and attaches it to request state.

    Downstream dependencies can then call ``get_tenant_db`` with
    ``request.state.tenant_id`` to get a properly scoped session.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tenant_id: UUID | None = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                from .auth_service import verify_token
                payload = verify_token(token)
                raw = payload.get("tenant_id")
                if raw:
                    tenant_id = UUID(str(raw))
            except (HTTPException, ValueError):
                pass  # Let route handlers deal with auth errors

        request.state.tenant_id = tenant_id
        return await call_next(request)
