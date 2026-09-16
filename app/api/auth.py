"""
auth.py
=======
Authentication API routes for the Distributed File Storage System (DFSS).
Implements Section 26 user login and JWT issuance flow:
- POST /auth/login (and /login alias)
- Constant-time verification preventing user enumeration.
- Rejection of inactive/disabled user accounts.
- JWT issuance containing user id and role claims.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.config import get_jwt_expiry_minutes
from app.models.user_model import LoginRequest, LoginResponse
from app.services.auth_service import verify_password
from app.services.jwt_service import create_access_token
from app.services.user_storage import get_user_by_username

router = APIRouter(tags=["Authentication"])

# Pre-computed valid dummy bcrypt hash to ensure constant-time response on non-existent users
# (prevents user enumeration via timing attacks)
_DUMMY_HASH = "$2b$12$0Gq0v3mR9Jq6Y7zL5H2bte7wX1a3k4j5l6m7n8o9p0q1r2s3t4u5v"


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
