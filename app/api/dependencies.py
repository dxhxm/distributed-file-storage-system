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
    Returns a dependency enforcing that the caller belongs to at least one of the allowed roles.
    """
    normalized_roles: Set[str] = {
        r.value if hasattr(r, "value") else str(r) for r in allowed_roles
    }

    async def role_checker(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if current_user.role not in normalized_roles:
            detail_msg = (
                "Admin privileges required"
                if normalized_roles == {"ADMIN"}
                else "Forbidden: Insufficient privileges"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail_msg,
            )
        return current_user

    return role_checker


# Pre-configured RBAC dependencies
require_admin = require_role(Role.ADMIN, "ADMIN")
