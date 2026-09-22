"""
dependencies.py
===============
FastAPI dependencies for JWT authentication, role verification, and request context injection.
Implements Section 26 JWT validation dependency:
- Decodes and verifies the bearer token on protected routes.
- Distinguishable error codes on missing (NOT_AUTHENTICATED), expired (TOKEN_EXPIRED), and malformed (INVALID_TOKEN) tokens.
- Attaches the authenticated user and role to the request context (request.state.user / request.state.role).
- Role-based access control (RBAC) helpers (require_admin, require_role).
"""

from typing import Any, Dict, Optional, Set, Union
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from app.models.user_model import Role
from app.services.jwt_service import (
    TokenExpiredError,
    TokenInvalidError,
    decode_access_token,
)

security = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """
    Representation of an authenticated user extracted from a valid JWT access token.
    """
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(..., description="Unique user identifier ('sub' claim)")
    role: str = Field(..., description="Assigned user role (USER, ADMIN, SYSTEM)")
    username: Optional[str] = Field(default=None, description="Username handle if present in token")
    claims: Dict[str, Any] = Field(default_factory=dict, description="Complete dictionary of token claims")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthenticatedUser:
    """
    FastAPI dependency that extracts, decodes, and verifies the JWT bearer token.

    Behavior:
    - Missing token: Raises HTTP 401 with 'NOT_AUTHENTICATED' code.
    - Expired token: Raises HTTP 401 with distinguishable 'TOKEN_EXPIRED' code.
    - Malformed/tampered token: Raises HTTP 401 with 'INVALID_TOKEN' code.
    - Valid token: Attaches user and role to request.state and returns AuthenticatedUser.
    """
    if not credentials or not credentials.credentials or not credentials.credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NOT_AUTHENTICATED",
            headers={"WWW-Authenticate": "Bearer", "X-Error-Code": "NOT_AUTHENTICATED"},
        )

    raw_token = credentials.credentials.strip()

    try:
        payload = decode_access_token(raw_token)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="TOKEN_EXPIRED",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token expired"',
                "X-Error-Code": "TOKEN_EXPIRED",
            },
        ) from exc
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_TOKEN",
            headers={"WWW-Authenticate": "Bearer", "X-Error-Code": "INVALID_TOKEN"},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_TOKEN",
            headers={"WWW-Authenticate": "Bearer", "X-Error-Code": "INVALID_TOKEN"},
        ) from exc

    # Construct authenticated user context
    auth_user = AuthenticatedUser(
        user_id=str(payload["sub"]),
        role=str(payload["role"]),
        username=payload.get("username"),
        claims=payload,
    )

    # Attach to request state for downstream handlers and middleware
    request.state.user = auth_user
    request.state.role = auth_user.role

    return auth_user


def require_role(*allowed_roles: Union[str, Role]):
    """
    Returns a FastAPI dependency enforcing that the caller belongs to at least one of the allowed roles.

    Composes cleanly with `get_current_user` to ensure caller is authenticated and possesses
    one of the specified roles (USER, ADMIN, SYSTEM).

    - If caller is unauthenticated (missing/invalid/expired token): `get_current_user` raises 401.
    - If caller is authenticated but role is not allowed: raises HTTP 403 Forbidden with 'X-Error-Code: FORBIDDEN'.
    """
    if not allowed_roles:
        raise ValueError("require_role requires at least one allowed role specification")

    normalized_roles: Set[str] = set()
    for r in allowed_roles:
        if isinstance(r, Role):
            normalized_roles.add(r.value)
        elif isinstance(r, str):
            normalized_roles.add(r.strip().upper())
        elif hasattr(r, "value"):
            normalized_roles.add(str(r.value).strip().upper())
        else:
            normalized_roles.add(str(r).strip().upper())

    async def role_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        user_role = current_user.role.strip().upper() if isinstance(current_user.role, str) else str(current_user.role)
        if user_role not in normalized_roles:
            if normalized_roles == {"ADMIN"}:
                detail_msg = "Admin privileges required"
                err_code = "FORBIDDEN"
            elif normalized_roles == {"SYSTEM"}:
                detail_msg = "System credential required for internal node RPC"
                err_code = "FORBIDDEN_SYSTEM_REQUIRED"
            elif normalized_roles == {"USER"}:
                detail_msg = "User privileges required"
                err_code = "FORBIDDEN_USER_REQUIRED"
            else:
                detail_msg = "Forbidden: Insufficient privileges"
                err_code = "FORBIDDEN"

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail_msg,
                headers={"X-Error-Code": err_code},
            )
        return current_user

    return role_checker


# Pre-configured RBAC dependencies
require_admin = require_role(Role.ADMIN)
require_user = require_role(Role.USER)
require_system = require_role(Role.SYSTEM)


async def require_human_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """
    Dependency enforcing that the caller is a human user (USER or ADMIN).
    Rejects SYSTEM service tokens with HTTP 403 Forbidden.
    """
    user_role = current_user.role.strip().upper() if isinstance(current_user.role, str) else str(current_user.role)
    if user_role not in {Role.USER.value, Role.ADMIN.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User session required; SYSTEM credentials not permitted on user routes",
            headers={"X-Error-Code": "FORBIDDEN_USER_REQUIRED"},
        )
    return current_user



