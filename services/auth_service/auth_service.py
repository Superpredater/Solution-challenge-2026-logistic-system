"""JWT authentication service using RS256 with Redis-backed refresh token storage."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import redis.asyncio as aioredis
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, status
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

def _load_or_generate_keys() -> Tuple[str, str]:
    """Load RSA keys from env vars or generate a dev keypair."""
    private_pem = os.environ.get("PRIVATE_KEY_PEM")
    public_pem = os.environ.get("PUBLIC_KEY_PEM")

    if private_pem and public_pem:
        return private_pem, public_pem

    # Dev mode: generate ephemeral keypair
    logger.warning("RSA keys not found in env — generating ephemeral dev keypair")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


PRIVATE_KEY_PEM, PUBLIC_KEY_PEM = _load_or_generate_keys()
ALGORITHM = "RS256"
REFRESH_TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 days


# ---------------------------------------------------------------------------
# Redis client (lazy singleton)
# ---------------------------------------------------------------------------

_redis_client: Optional[aioredis.Redis] = None


def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        from services.shared.config import settings
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token(
    stakeholder_id: str,
    tenant_id: str,
    role: str,
    expiry_minutes: int = 60,
) -> str:
    """Issue an RS256-signed access JWT."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": stakeholder_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expiry_minutes),
        "type": "access",
    }
    return jwt.encode(payload, PRIVATE_KEY_PEM, algorithm=ALGORITHM)


def create_refresh_token(stakeholder_id: str, tenant_id: str) -> str:
    """Issue an RS256-signed refresh JWT with 7-day expiry."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": stakeholder_id,
        "tenant_id": tenant_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=REFRESH_TOKEN_TTL_SECONDS),
        "type": "refresh",
    }
    return jwt.encode(payload, PRIVATE_KEY_PEM, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

def verify_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTP 401 on failure."""
    try:
        payload = jwt.decode(token, PUBLIC_KEY_PEM, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# Refresh token storage helpers
# ---------------------------------------------------------------------------

async def store_refresh_token(token: str, stakeholder_id: str) -> None:
    """Persist refresh token JTI in Redis with TTL."""
    payload = verify_token(token)
    jti = payload.get("jti")
    if not jti:
        return
    redis = _get_redis()
    await redis.setex(f"refresh:{jti}", REFRESH_TOKEN_TTL_SECONDS, stakeholder_id)


async def revoke_refresh_token(token: str) -> None:
    """Remove refresh token from Redis (logout / rotation)."""
    try:
        payload = verify_token(token)
    except HTTPException:
        return
    jti = payload.get("jti")
    if jti:
        redis = _get_redis()
        await redis.delete(f"refresh:{jti}")


async def _is_refresh_token_valid(token: str) -> bool:
    """Return True if the refresh token JTI exists in Redis."""
    try:
        payload = verify_token(token)
    except HTTPException:
        return False
    jti = payload.get("jti")
    if not jti:
        return False
    redis = _get_redis()
    return await redis.exists(f"refresh:{jti}") == 1


# ---------------------------------------------------------------------------
# Token rotation
# ---------------------------------------------------------------------------

async def rotate_refresh_token(refresh_token: str) -> Tuple[str, str]:
    """Validate old refresh token, revoke it, and issue a new pair."""
    if not await _is_refresh_token_valid(refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or has been revoked",
        )
    payload = verify_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token",
        )

    stakeholder_id = payload["sub"]
    tenant_id = payload["tenant_id"]

    await revoke_refresh_token(refresh_token)

    from services.shared.config import settings
    new_access = create_access_token(
        stakeholder_id, tenant_id, payload.get("role", "Viewer"),
        expiry_minutes=settings.jwt_expiry_minutes,
    )
    new_refresh = create_refresh_token(stakeholder_id, tenant_id)
    await store_refresh_token(new_refresh, stakeholder_id)
    return new_access, new_refresh


# ---------------------------------------------------------------------------
# Convenience class
# ---------------------------------------------------------------------------

class AuthService:
    """Thin facade over module-level functions for DI / testing."""

    create_access_token = staticmethod(create_access_token)
    create_refresh_token = staticmethod(create_refresh_token)
    verify_token = staticmethod(verify_token)
    rotate_refresh_token = staticmethod(rotate_refresh_token)
    store_refresh_token = staticmethod(store_refresh_token)
    revoke_refresh_token = staticmethod(revoke_refresh_token)
