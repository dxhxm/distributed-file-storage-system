"""
user_model.py
=============
Pydantic data models and enums for authentication and authorization in DFSS.
Defines:
- Role: Enumeration with exact USER, ADMIN, and SYSTEM roles per Section 26.
- User: Pydantic model carrying hashed_password only (never plaintext password).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    """
    Role enumeration defining user authorization tiers in DFSS per Section 26.
    Exact roles:
    - USER: Standard end-user with normal read/write storage access.
    - ADMIN: Cluster administrator with elevated node and user management privileges.
    - SYSTEM: Internal system / inter-node automated service account.
    """
    USER = "USER"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class User(BaseModel):
    """
    Pydantic data model representing a user entity.
    Security invariant: Stores hashed_password only, never plaintext passwords.
    """
    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        populate_by_name=True
    )

    username: str = Field(..., min_length=1, description="Unique username of the user account")
    hashed_password: str = Field(..., min_length=1, description="Cryptographic hash of the user password")
    role: Role = Field(default=Role.USER, description="Assigned role (USER, ADMIN, or SYSTEM)")
    is_active: bool = Field(default=True, description="Account active status")
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the user account was created"
    )


class LoginRequest(BaseModel):
    """
    Schema for user authentication request payload.
    """
    username: str = Field(..., min_length=1, description="Account username")
    password: str = Field(..., min_length=1, description="Plaintext password for verification")


class LoginResponse(BaseModel):
    """
    Schema for user authentication response upon successful login or token refresh.
    """
    access_token: str = Field(..., description="Signed JWT bearer access token")
    refresh_token: Optional[str] = Field(default=None, description="Signed JWT refresh token")
    token_type: str = Field(default="bearer", description="Token authorization type")
    role: str = Field(..., description="Assigned user role (USER, ADMIN, SYSTEM)")
    username: str = Field(..., description="Username of the authenticated account")
    user_id: str = Field(..., description="Unique user identifier")
    expires_in_minutes: int = Field(..., description="Token lifespan duration in minutes")


class RefreshTokenRequest(BaseModel):
    """
    Schema for refreshing access tokens via a valid refresh token.
    """
    refresh_token: str = Field(..., min_length=1, description="Valid JWT refresh token")


class CreateUserRequest(BaseModel):
    """
    Schema for admin-only user provisioning request.
    """
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    username: str = Field(..., min_length=1, description="Unique username for the new account")
    password: str = Field(..., min_length=1, description="Initial plaintext password to be hashed")
    role: Role = Field(default=Role.USER, description="Assigned authorization role (USER, ADMIN, SYSTEM)")
    is_active: bool = Field(default=True, description="Account active status")


class UserResponse(BaseModel):
    """
    Public user entity response schema (never exposes password or hash).
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique user ID")
    username: str = Field(..., description="Username of the user account")
    role: str = Field(..., description="Assigned role")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    is_active: bool = Field(..., description="Account active status")
