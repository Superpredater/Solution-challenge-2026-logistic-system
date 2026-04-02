"""Auth router — login, refresh, logout, MFA setup/verify."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.config import settings
from services.shared.database import AsyncSessionLocal
from services.shared.orm_models import StakeholderORM, TenantORM

from .auth_service import (
    AuthService,
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    store_refresh_token,
    verify_token,
)
from .mfa import enforce_mfa_gate, generate_mfa_secret, verify_totp
from .rbac import get_current_stakeholder

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class MFASetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class MFAVerifyRequest(BaseModel):
    totp_code: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def _fetch_stakeholder_by_email(session: AsyncSession, email: str) -> StakeholderORM | None:
    result = await session.execute(
        select(StakeholderORM).where(StakeholderORM.email == email)
    )
    return result.scalar_one_or_none()


async def _fetch_tenant(session: AsyncSession, tenant_id: UUID) -> TenantORM | None:
    result = await session.execute(
        select(TenantORM).where(TenantORM.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(_get_session),
) -> TokenResponse:
    """Authenticate stakeholder, enforce MFA if required, return token pair."""
    stakeholder = await _fetch_stakeholder_by_email(session, body.email)
    if not stakeholder:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # StakeholderORM doesn't store password_hash in the current schema;
    # we check for a `password_hash` attribute gracefully.
    password_hash: str | None = getattr(stakeholder, "password_hash", None)
    if password_hash and not _verify_password(body.password, password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    tenant_orm = await _fetch_tenant(session, stakeholder.tenant_id)
    if tenant_orm:
        from services.shared.models import Tenant
        from datetime import datetime, timezone
        tenant = Tenant(
            tenant_id=tenant_orm.tenant_id,
            name=tenant_orm.name,
            mfa_enabled=tenant_orm.mfa_enabled,
            eco_routing_enabled=tenant_orm.eco_routing_enabled,
            autonomous_decision_enabled=tenant_orm.autonomous_decision_enabled,
            risk_score_weights=tenant_orm.risk_score_weights or {},
            api_rate_limit_per_minute=tenant_orm.api_rate_limit_per_minute,
            quiet_period_start=tenant_orm.quiet_period_start,
            quiet_period_end=tenant_orm.quiet_period_end,
            custom_risk_thresholds=tenant_orm.custom_risk_thresholds or [],
            created_at=tenant_orm.created_at,
            updated_at=tenant_orm.updated_at,
        )
        enforce_mfa_gate(tenant, body.totp_code, stakeholder.mfa_secret)

    access_token = create_access_token(
        stakeholder_id=str(stakeholder.stakeholder_id),
        tenant_id=str(stakeholder.tenant_id),
        role=stakeholder.role,
        expiry_minutes=settings.jwt_expiry_minutes,
    )
    refresh_token = create_refresh_token(
        stakeholder_id=str(stakeholder.stakeholder_id),
        tenant_id=str(stakeholder.tenant_id),
    )
    await store_refresh_token(refresh_token, str(stakeholder.stakeholder_id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    """Rotate refresh token and return a new access+refresh pair."""
    new_access, new_refresh = await rotate_refresh_token(body.refresh_token)
    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest) -> None:
    """Invalidate the provided refresh token."""
    await revoke_refresh_token(body.refresh_token)


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    principal: tuple = Depends(get_current_stakeholder),
    session: AsyncSession = Depends(_get_session),
) -> MFASetupResponse:
    """Generate a new TOTP secret for the authenticated stakeholder."""
    stakeholder_id, _tenant_id, _role = principal
    stakeholder = await session.get(StakeholderORM, UUID(stakeholder_id))
    if not stakeholder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stakeholder not found")

    secret = generate_mfa_secret()
    import pyotp
    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(name=stakeholder.email, issuer_name="SmartSupplyChain")

    # Persist secret (not yet verified/active until /mfa/verify is called)
    stakeholder.mfa_secret = secret
    await session.commit()

    return MFASetupResponse(secret=secret, otpauth_url=otpauth_url)


@router.post("/mfa/verify", status_code=status.HTTP_200_OK)
async def mfa_verify(
    body: MFAVerifyRequest,
    principal: tuple = Depends(get_current_stakeholder),
    session: AsyncSession = Depends(_get_session),
) -> dict:
    """Verify TOTP code and confirm MFA is configured."""
    stakeholder_id, _tenant_id, _role = principal
    stakeholder = await session.get(StakeholderORM, UUID(stakeholder_id))
    if not stakeholder or not stakeholder.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated — call /mfa/setup first",
        )

    if not verify_totp(stakeholder.mfa_secret, body.totp_code):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid TOTP code")

    return {"mfa_configured": True}
