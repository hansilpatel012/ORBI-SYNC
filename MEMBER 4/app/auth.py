from enum import Enum
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import settings
from app.db import get_supabase_client

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Enter your Bearer token (Admin API Key, Operator API Key, or Supabase Auth JWT)",
)


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class AuthUser(BaseModel):
    """Authenticated user profile with verified role."""

    id: str
    email: Optional[str] = None
    role: str

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value

    def is_operator(self) -> bool:
        return self.role in (UserRole.OPERATOR.value, UserRole.ADMIN.value)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> AuthUser:
    """
    Validates authentication credentials and determines user role securely on the server.
    CRITICAL: Never trusts client-supplied headers or body fields for role assignment.

    Authentication order:
    1. Server-side configured ADMIN_API_KEY or SUPABASE_SECRET_KEY -> 'admin'
    2. Server-side configured OPERATOR_API_KEY -> 'operator'
    3. Official Supabase Auth JWT token verified via Supabase Auth server ->
       extracts role exclusively from server-controlled `app_metadata` (never `user_metadata`).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()

    # 1. Check server-configured admin keys
    if (settings.supabase_secret_key and token == settings.supabase_secret_key) or (
        settings.admin_api_key and token == settings.admin_api_key
    ):
        return AuthUser(id="service-admin", email="admin@orbi-sync.local", role=UserRole.ADMIN.value)

    # 2. Check server-configured operator keys
    if settings.operator_api_key and token == settings.operator_api_key:
        return AuthUser(
            id="service-operator",
            email="operator@orbi-sync.local",
            role=UserRole.OPERATOR.value,
        )

    # 3. Check Supabase Auth JWT token
    try:
        client = get_supabase_client()
        auth_response = client.auth.get_user(token)
        if auth_response and getattr(auth_response, "user", None):
            user = auth_response.user
            # In Supabase Auth, `user_metadata` is client-modifiable.
            # `app_metadata` is ONLY modifiable by service role or database triggers.
            app_meta = getattr(user, "app_metadata", {}) or {}
            verified_role = app_meta.get("role") or app_meta.get("roles")

            if isinstance(verified_role, list):
                verified_role = verified_role[0] if verified_role else None

            # Map or default role
            role_str = str(verified_role).lower() if verified_role else UserRole.OPERATOR.value
            return AuthUser(
                id=str(user.id),
                email=getattr(user, "email", None),
                role=role_str,
            )
    except Exception:
        # Pass through to unauthorized rejection below
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(allowed_roles: List[str]):
    """
    Role-based authorization dependency factory.
    Enforces that the server-verified role is within `allowed_roles`.
    """

    def role_dependency(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden: Insufficient privileges for this operation. "
                    f"Required role in {allowed_roles}, your role is '{user.role}'."
                ),
            )
        return user

    return role_dependency


# Preconfigured role dependencies for route protection
require_operator = require_roles([UserRole.OPERATOR.value, UserRole.ADMIN.value])
require_admin = require_roles([UserRole.ADMIN.value])
