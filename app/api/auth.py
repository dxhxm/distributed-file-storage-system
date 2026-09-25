"""
auth.py
=======
Authentication API routes for the Distributed File Storage System (DFSS).
Implements Section 26 user authentication, RBAC authorization, and user management:
- POST /auth/login (and /login alias)
- POST /auth/users (and /users alias) restricted strictly to ADMIN role
- GET /auth/me (and /me alias) returning authenticated session profile
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    AuthenticatedUser,
    get_current_user,
    require_admin,
    require_human_user,
    require_role,
)
from app.models.config import get_jwt_expiry_minutes
from app.models.user_model import (
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    User,
    UserResponse,
)
from app.services.auth_service import hash_password, verify_password
from app.services.jwt_service import (
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.services.user_storage import (
    create_user,
    get_user_by_id,
    get_user_by_username,
)

router = APIRouter(tags=["Authentication"])

# Pre-computed valid dummy bcrypt hash to ensure constant-time response on non-existent users
# (prevents user enumeration via timing attacks)
_DUMMY_HASH = "$2b$12$0Gq0v3mR9Jq6Y7zL5H2bte7wX1a3k4j5l6m7n8o9p0q1r2s3t4u5v"


@router.post("/auth/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
async def login(credentials: LoginRequest):
    """
    Authenticate user with username and password, returning a signed JWT access token and refresh token.

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
            headers={"WWW-Authenticate": "Bearer", "X-Error-Code": "INVALID_CREDENTIALS"},
        )

    # Verify password hash
    is_valid = verify_password(credentials.password, user["hashed_password"])
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer", "X-Error-Code": "INVALID_CREDENTIALS"},
        )

    # Reject inactive accounts
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled or inactive",
            headers={"WWW-Authenticate": "Bearer", "X-Error-Code": "ACCOUNT_DISABLED"},
        )


    # Issue signed JWT access token and refresh token
    access_token = create_access_token(
        user_id=user["id"],
        role=user["role"],
        username=user["username"]
    )
    refresh_token = create_refresh_token(
        user_id=user["id"],
        role=user["role"],
        username=user["username"]
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user["role"],
        username=user["username"],
        user_id=user["id"],
        expires_in_minutes=get_jwt_expiry_minutes(),
    )


@router.post("/auth/refresh", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@router.post("/refresh", response_model=LoginResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
async def refresh_access_token(payload: RefreshTokenRequest):
    """
    Exchange a valid, unexpired refresh token for a newly issued access token.
    Validates that the user account exists and remains active/non-revoked.
    """
    try:
        claims = decode_refresh_token(payload.refresh_token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer error=\"token_expired\""},
        )
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    user_id = claims["sub"]
    user = get_user_by_id(user_id)

    # Reject non-existent or inactive / revoked users
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled, inactive, or revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue fresh access token and rotated refresh token with current user record state
    new_access_token = create_access_token(
        user_id=user["id"],
        role=user["role"],
        username=user["username"],
    )
    new_refresh_token = create_refresh_token(
        user_id=user["id"],
        role=user["role"],
        username=user["username"],
    )

    return LoginResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
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
    current_user: AuthenticatedUser = Depends(require_admin),
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


@router.get("/auth/me", response_model=AuthenticatedUser, status_code=status.HTTP_200_OK)
@router.get("/me", response_model=AuthenticatedUser, status_code=status.HTTP_200_OK, include_in_schema=False)
async def get_my_profile(
    current_user: AuthenticatedUser = Depends(require_human_user),
):
    """
    Returns the authenticated user profile and claims attached to the active JWT session.
    Restricted to human user accounts (USER or ADMIN); SYSTEM tokens cannot access user profiles.
    """
    return current_user

