"""Auth service package — JWT, MFA, RBAC, tenant RLS."""

from .auth_service import AuthService
from .rbac import get_current_stakeholder, require_permission

__all__ = ["AuthService", "get_current_stakeholder", "require_permission"]
