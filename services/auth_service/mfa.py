"""TOTP-based MFA helpers using pyotp."""

from __future__ import annotations

from typing import Optional

import pyotp
from fastapi import HTTPException, status

from services.shared.models import Tenant


def generate_mfa_secret() -> str:
    """Generate a random base32 TOTP secret."""
    return pyotp.random_base32()


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code with a ±1 window tolerance."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def is_mfa_required(tenant: Tenant) -> bool:
    """Return True if the tenant has MFA enforcement enabled."""
    return tenant.mfa_enabled


def enforce_mfa_gate(tenant: Tenant, totp_code: Optional[str], mfa_secret: Optional[str]) -> None:
    """Raise HTTP 403 if MFA is required but the code is missing or invalid.

    Args:
        tenant: The tenant configuration.
        totp_code: The TOTP code provided by the stakeholder (may be None).
        mfa_secret: The stakeholder's stored TOTP secret (may be None if not configured).
    """
    if not is_mfa_required(tenant):
        return

    if not totp_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA code required",
        )

    if not mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA not configured for this account",
        )

    if not verify_totp(mfa_secret, totp_code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid MFA code",
        )
