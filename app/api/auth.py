"""
auth.py
=======
Authentication API routes for the Distributed File Storage System (DFSS).
Implements Section 26 user authentication, RBAC authorization, and user management:
- POST /auth/login (and /login alias)
- POST /auth/users (and /users alias) restricted strictly to ADMIN role
- Security dependencies for JWT bearer extraction and role-based access control.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.config import get_jwt_expiry_minutes
from app.models.user_model import (
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    User,
    UserResponse,
)
from app.services.auth_service import hash_password, verify_password
from app.services.jwt_service import (
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    decode_access_token,
)
from app.services.user_storage import create_user, get_user_by_username

router = APIRouter(tags=["Authentication"])
security = HTTPBearer(auto_error=False)

# Pre-computed valid dummy bcrypt hash to ensure constant-time response on non-existent users
# (prevents user enumeration via timing attacks)
_DUMMY_HASH = "$2b$12$0Gq0v3mR9Jq6Y7zL5H2bte7wX1a3k4j5l6m7n8o9p0q1r2s3t4u5v"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    Extracts and validates the JWT bearer token from the Authorization header.
    Returns the decoded token payload dictionary.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        return payload
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Enforces that the authenticated user possesses the ADMIN role.
    Raises HTTP 403 Forbidden for non-admin callers.
    """
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


@router.post("/auth/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
async def login(credentials: LoginRequest):
    """
    Authenticate user with username and password, returning a signed JWT access token.

    Security guarantees:
    - Zero user-enumeration: Returns identical 401 error for non-existent users and wrong passwords.
    - Constant-time computation regardless of user existence.
    - Rejects inactive or suspended user accounts.
    """
    user = get_user_by_username(credentials.username)

    if not user:
        # Perform dummy verification to mitigate timing-based user enumeration
        verify_password(credentials.password, _DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password hash
    is_valid = verify_password(credentials.password, user["hashed_password"])
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reject inactive accounts
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue signed JWT access token
    token = create_access_token(
        user_id=user["id"],
        role=user["role"],
        username=user["username"]
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        username=user["username"],
        user_id=user["id"],
        expires_in_minutes=get_jwt_expiry_minutes(),
    )


@router.post("/auth/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_user_account(
    payload: CreateUserRequest,
    current_user: Dict[str, Any] = Depends(require_admin),
):
    """
    Provision a new user account on the cluster.
    Strictly restricted to authenticated cluster administrators (ADMIN role).

    - Rejects non-admin callers with HTTP 403 Forbidden.
    - Rejects unauthenticated callers with HTTP 401 Unauthorized.
    - Rejects duplicate usernames cleanly with HTTP 409 Conflict.
    - Never returns password or hashed_password in the response.
    """
    # 1. Check for duplicate username
    existing_user = get_user_by_username(payload.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with username '{payload.username}' already exists",
        )

    # 2. Hash plaintext password
    hashed_pwd = hash_password(payload.password)

    # 3. Instantiate model and persist to storage
    user_model = User(
        username=payload.username,
        hashed_password=hashed_pwd,
        role=payload.role,
        is_active=payload.is_active,
    )

    try:
        record = create_user(user_model)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return UserResponse(
        id=record["id"],
        username=record["username"],
        role=record["role"],
        created_at=record["created_at"],
        is_active=record["is_active"],
    )
