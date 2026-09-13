"""
auth_service.py
===============
Cryptographic password hashing and verification services using bcrypt.
Guarantees:
- One-way hashing with unique automatic per-hash salting (never returns identical hash twice).
- Constant-time verification preventing timing attacks.
- Robust handling of invalid/malformed hashes.
- Absolute prevention of plaintext password logging.
"""

import logging
from typing import Any
import bcrypt

logger = logging.getLogger("auth_service")


def hash_password(plain_password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with a cryptographically secure random salt.

    Args:
        plain_password: The plaintext password string to hash.

    Returns:
        A securely salted, non-reversible bcrypt hash string (e.g. '$2b$12$...').

    Raises:
        ValueError: If plain_password is not a valid non-empty string.
    """
    if not isinstance(plain_password, str) or len(plain_password) == 0:
        raise ValueError("Password must be a non-empty string")

    # bcrypt max length is 72 bytes; encode to utf-8 bytes
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode("utf-8")


def verify_password(plain_password: Any, hashed_password: Any) -> bool:
    """
    Verifies a plaintext password against a stored bcrypt hash.

    Args:
        plain_password: The plaintext password string to verify.
        hashed_password: The stored bcrypt hash string.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False

    if len(plain_password) == 0 or len(hashed_password) == 0:
        return False

    try:
        password_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as exc:
        # Note: Deliberately do NOT log plain_password or sensitive input details
        logger.warning("Password verification failed due to invalid hash format or processing error: %s", type(exc).__name__)
        return False
