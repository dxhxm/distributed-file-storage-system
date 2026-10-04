"""
auth.py
=======
Authentication API routes for the Distributed File Storage System (DFSS).
Implements Section 26 user authentication, RBAC authorization, and user management:
- POST /auth/login (and /login alias)
- POST /auth/users (and /users alias) restricted strictly to ADMIN role
- GET /auth/me (and /me alias) returning authenticated session profile
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status

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
    Role,
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
    User,
    UserResponse,
)
from app.services import log_service
from app.services.auth_service import hash_password, verify_password
from app.services.jwt_service import (
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.services.rate_limiter import auth_rate_limiter
from app.services.user_storage import (
    count_active_admins,
    create_user,
    get_user_by_id,
    get_user_by_id_or_username,
    get_user_by_username,
    list_users,
    update_user_role,
    update_user_status,
)

router = APIRouter(tags=["Authentication"])

# Pre-computed valid dummy bcrypt hash to ensure constant-time response on non-existent users
# (prevents user enumeration via timing attacks)
_DUMMY_HASH = "$2b$12$0Gq0v3mR9Jq6Y7zL5H2bte7wX1a3k4j5l6m7n8o9p0q1r2s3t4u5v"


def _get_client_source_identifier(request: Request) -> str:
    """Extracts client IP or origin host for brute-force rate limiting."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown_client"


@router.post("/auth/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
async def login(credentials: LoginRequest, request: Request):
    """
    Authenticate user with username and password, returning a signed JWT access token and refresh token.

    Security guarantees:
    - Section 33 Brute-force protection: Rate limits and temporarily locks sources after repeated failed attempts.
    - Zero user-enumeration: Returns identical 401 error for non-existent users and wrong passwords.
    - Constant-time computation regardless of user existence.
    - Rejects inactive or suspended user accounts.
    """
    source_key = _get_client_source_identifier(request)

    # 1. Enforce rate limiting and brute-force lockout
    is_limited, retry_after = auth_rate_limiter.is_rate_limited(source_key)
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please try again in {retry_after} seconds.",
            headers={
                "Retry-After": str(retry_after),
                "X-Error-Code": "RATE_LIMITED",
            },
        )

    user = get_user_by_username(credentials.username)

    if not user:
        # Perform dummy verification to mitigate timing-based user enumeration
        verify_password(credentials.password, _DUMMY_HASH)
        auth_rate_limiter.record_failed_attempt(source_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer", "X-Error-Code": "INVALID_CREDENTIALS"},
        )

    # Verify password hash
    is_valid = verify_password(credentials.password, user["hashed_password"])
    if not is_valid:
        auth_rate_limiter.record_failed_attempt(source_key)
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

    # 2. Reset rate limit failure counters upon successful authentication
    auth_rate_limiter.record_successful_attempt(source_key)

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


@router.get("/auth/users", response_model=List[UserResponse], status_code=status.HTTP_200_OK)
@router.get("/users", response_model=List[UserResponse], status_code=status.HTTP_200_OK, include_in_schema=False)
async def get_all_users(
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    List all user accounts in the cluster.
    Strictly restricted to authenticated cluster administrators (ADMIN role).
    """
    records = list_users()
    return [
        UserResponse(
            id=r["id"],
            username=r["username"],
            role=r["role"],
            created_at=r["created_at"],
            is_active=r["is_active"],
        )
        for r in records
    ]


@router.put("/auth/users/{identifier}/role", response_model=UserResponse, status_code=status.HTTP_200_OK)
@router.post("/auth/users/{identifier}/role", response_model=UserResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
@router.put("/users/{identifier}/role", response_model=UserResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
@router.post("/users/{identifier}/role", response_model=UserResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
async def change_user_role(
    identifier: str,
    payload: UpdateUserRoleRequest,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Change the assigned role of a user.
    Strictly restricted to authenticated cluster administrators (ADMIN role).

    DoD Invariant:
    An admin cannot demote the last remaining ADMIN account, avoiding a lockout.
    """
    user = get_user_by_id_or_username(identifier)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{identifier}' not found",
        )

    target_role_str = payload.role.value if hasattr(payload.role, "value") else str(payload.role)

    # Lockout check: if demoting an active ADMIN to non-ADMIN, ensure at least 1 other active ADMIN remains
    if user["role"] == Role.ADMIN.value and user["is_active"] and target_role_str != Role.ADMIN.value:
        active_admins = count_active_admins()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last remaining active ADMIN account to avoid system lockout",
            )

    updated = update_user_role(user["id"], payload.role)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{identifier}' not found",
        )

    # Audit logging
    log_service.record_audit(
        actor_id=current_user.user_id,
        actor_username=current_user.username or current_user.user_id,
        action="UPDATE_USER_ROLE",
        target=f"/auth/users/{user['id']}/role",
        details={
            "target_user_id": user["id"],
            "target_username": user["username"],
            "previous_role": user["role"],
            "new_role": target_role_str,
        },
    )

    return UserResponse(
        id=updated["id"],
        username=updated["username"],
        role=updated["role"],
        created_at=updated["created_at"],
        is_active=updated["is_active"],
    )


@router.post("/auth/users/{identifier}/deactivate", response_model=UserResponse, status_code=status.HTTP_200_OK)
@router.post("/users/{identifier}/deactivate", response_model=UserResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
async def deactivate_user_account(
    identifier: str,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Deactivate a user account on the cluster.
    Strictly restricted to authenticated cluster administrators (ADMIN role).

    DoD Invariant:
    An admin cannot deactivate the last remaining active ADMIN account, avoiding a lockout.
    """
    return await _set_user_active_status(identifier, is_active=False, current_user=current_user)


@router.put("/auth/users/{identifier}/status", response_model=UserResponse, status_code=status.HTTP_200_OK)
@router.put("/users/{identifier}/status", response_model=UserResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
async def update_user_account_status(
    identifier: str,
    payload: UpdateUserStatusRequest,
    current_user: AuthenticatedUser = Depends(require_admin),
):
    """
    Update active status (activate/deactivate) of a user account.
    Strictly restricted to authenticated cluster administrators (ADMIN role).
    """
    return await _set_user_active_status(identifier, is_active=payload.is_active, current_user=current_user)


async def _set_user_active_status(
    identifier: str,
    is_active: bool,
    current_user: AuthenticatedUser,
) -> UserResponse:
    user = get_user_by_id_or_username(identifier)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{identifier}' not found",
        )

    # Lockout check: if deactivating an active ADMIN, ensure at least 1 other active ADMIN remains
    if user["role"] == Role.ADMIN.value and user["is_active"] and not is_active:
        active_admins = count_active_admins()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last remaining active ADMIN account to avoid system lockout",
            )

    updated = update_user_status(user["id"], is_active)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{identifier}' not found",
        )

    # Audit logging
    log_service.record_audit(
        actor_id=current_user.user_id,
        actor_username=current_user.username or current_user.user_id,
        action="DEACTIVATE_USER" if not is_active else "ACTIVATE_USER",
        target=f"/auth/users/{user['id']}/status",
        details={
            "target_user_id": user["id"],
            "target_username": user["username"],
            "is_active": is_active,
        },
    )

    return UserResponse(
        id=updated["id"],
        username=updated["username"],
        role=updated["role"],
        created_at=updated["created_at"],
        is_active=updated["is_active"],
    )


