"""
jwt_service.py
==============
JSON Web Token (JWT) encoding, decoding, and validation services for DFSS.
Implements the JWT session mechanism per Section 26:
- Issues tokens carrying 'sub' (user id) and 'role' claims.
- Validates token signatures in constant time.
- Enforces expiration with distinct catchable exceptions.
- Rejects tampered signatures or malformed tokens.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import jwt

from app.models.user_model import Role
from app.models.config import get_jwt_secret, get_jwt_expiry_minutes

# Configurable JWT parameters from environment variables
DEFAULT_JWT_ALGORITHM = "HS256"


class JWTError(Exception):
    """Base exception for all JWT-related errors in DFSS."""
    pass


class TokenExpiredError(JWTError):
    """Raised when a JWT access token has passed its expiration time ('exp')."""
    pass


class TokenInvalidError(JWTError):
    """Raised when a JWT signature is invalid, tampered with, or malformed."""
    pass


def get_jwt_algorithm() -> str:
    """Retrieves the active JWT algorithm."""
    return os.environ.get("JWT_ALGORITHM", DEFAULT_JWT_ALGORITHM)


def create_access_token(
    user_id: str,
    role: Union[str, Role],
    username: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
) -> str:
    """
    Creates and signs a JWT access token carrying sub (user id) and role claims.

    Args:
        user_id: The unique identifier of the user ('sub' claim).
        role: The user's role (USER, ADMIN, or SYSTEM).
        username: Optional username claim.
        expires_delta: Optional custom token lifespan; defaults to 60 minutes.
        extra_claims: Optional dictionary of additional claims.
        secret_key: Optional secret key override.
        algorithm: Optional signing algorithm override (default: HS256).

    Returns:
        Encoded JWT token string.

    Raises:
        ValueError: If user_id or role is empty or invalid.
    """
    if not user_id or not str(user_id).strip():
        raise ValueError("user_id ('sub' claim) must be a non-empty string")

    role_str = role.value if hasattr(role, "value") else str(role)
    if not role_str or not role_str.strip():
        raise ValueError("role claim must be a non-empty string")

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=get_jwt_expiry_minutes())

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "role": role_str,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    if username:
        payload["username"] = str(username)

    if extra_claims:
        for k, v in extra_claims.items():
            if k not in payload:
                payload[k] = v

    key = secret_key or get_jwt_secret()
    alg = algorithm or get_jwt_algorithm()

    return jwt.encode(payload, key, algorithm=alg)


def decode_access_token(
    token: str,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decodes, verifies the signature, and validates claims of a JWT access token.

    Args:
        token: The encoded JWT token string.
        secret_key: Optional secret key override.
        algorithm: Optional algorithm override.

    Returns:
        The decoded claims payload dictionary.

    Raises:
        TokenExpiredError: If the token has expired ('exp').
        TokenInvalidError: If the token signature is invalid, tampered, or malformed.
    """
    if not isinstance(token, str) or not token.strip():
        raise TokenInvalidError("Token must be a non-empty string")

    key = secret_key or get_jwt_secret()
    alg = algorithm or get_jwt_algorithm()

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[alg],
            options={"require": ["sub", "role", "exp", "iat"]}
        )
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError("Token has expired") from e
    except jwt.InvalidSignatureError as e:
        raise TokenInvalidError("Token signature is invalid or has been tampered with") from e
    except jwt.PyJWTError as e:
        raise TokenInvalidError(f"Invalid or malformed token: {str(e)}") from e

    # Extra validation for required claims
    if "sub" not in payload or "role" not in payload:
        raise TokenInvalidError("Token payload missing required 'sub' or 'role' claim")

    return payload
