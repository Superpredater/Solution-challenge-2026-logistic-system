"""API Gateway — VersioningMiddleware: adds API version headers."""

from __future__ import annotations

from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

CURRENT_VERSION = "v1"
DEPRECATED_VERSIONS = {"v0"}


class VersioningMiddleware(BaseHTTPMiddleware):
    """Adds X-API-Version header and Deprecation header for old version paths (Req 20.4)."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers["X-API-Version"] = CURRENT_VERSION

        # Check if the request path uses a deprecated version
        path = request.url.path
        for deprecated in DEPRECATED_VERSIONS:
            if f"/api/{deprecated}/" in path or path.startswith(f"/api/{deprecated}"):
                response.headers["Deprecation"] = (
                    f"This API version ({deprecated}) is deprecated. "
                    f"Please migrate to {CURRENT_VERSION}. "
                    "Support will be removed after 90 days."
                )
                break

        return response
