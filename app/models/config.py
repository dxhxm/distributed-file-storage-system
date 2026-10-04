"""
config.py
=========
Global configuration and environment secrets management for DFSS nodes.
Implements environment resolution and strict startup validation per Section 34.
"""

import os
from typing import Optional

# All node URLs must match the ports used by uvicorn in the node runner scripts
NODES = [
    "http://localhost:8000",  # Node A
    "http://localhost:8001",  # Node B
    "http://localhost:8002",  # Node C
]

# Determine current node from environment variable (set in each node runner script)
CURRENT_NODE = os.environ.get("CURRENT_NODE_URL", "http://localhost:8000")


def get_jwt_secret() -> str:
    """
    Retrieves the JWT signing secret from the environment.
    Raises RuntimeError loudly if JWT_SECRET is unset or empty per Section 34.
    """
    secret = os.environ.get("JWT_SECRET") or os.environ.get("JWT_SECRET_KEY")
    if not secret or not secret.strip():
        raise RuntimeError(
            "CRITICAL CONFIG ERROR: Missing required environment variable 'JWT_SECRET'. "
            "Server startup aborted per Section 34 security policy. "
            "Please configure JWT_SECRET in your environment or .env file."
        )
    return secret.strip()


def get_jwt_expiry_minutes() -> int:
    """
    Retrieves the configured JWT expiration duration in minutes (default: 60).
    """
    val = os.environ.get("JWT_EXPIRY_MINUTES", "60")
    try:
        return int(val)
    except (ValueError, TypeError):
        return 60


def get_admin_bootstrap_password() -> Optional[str]:
    """
    Retrieves the optional admin bootstrap password for first-boot provisioning.
    """
    pwd = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD")
    if pwd and pwd.strip():
        return pwd.strip()
    return None


def get_jwt_refresh_expiry_days() -> int:
    """
    Retrieves the configured refresh token validity duration in days (default: 7).
    """
    val = os.environ.get("JWT_REFRESH_EXPIRY_DAYS", "7")
    try:
        return int(val)
    except (ValueError, TypeError):
        return 7


def is_https_enforced() -> bool:
    """
    Determines if HTTPS/TLS is strictly enforced per Section 33 security layer.
    Enforces redirect/rejection of plain HTTP requests in production or when ENFORCE_HTTPS=true.
    """
    enforce = os.environ.get("ENFORCE_HTTPS", "").strip().lower()
    env = os.environ.get("ENVIRONMENT", "").strip().lower()
    return enforce in ("true", "1", "yes") or env == "production"


def is_cookie_secure() -> bool:
    """
    Determines if the Secure flag should be set on authentication cookies.
    Defaults to True when HTTPS is enforced or COOKIE_SECURE is explicitly true.
    """
    cookie_sec = os.environ.get("COOKIE_SECURE", "").strip().lower()
    if cookie_sec in ("true", "1", "yes"):
        return True
    if cookie_sec in ("false", "0", "no"):
        return False
    return is_https_enforced()


def get_hsts_max_age() -> int:
    """
    Retrieves the HSTS max-age duration in seconds (default: 31536000 = 1 year).
    """
    val = os.environ.get("HSTS_MAX_AGE", "31536000")
    try:
        return int(val)
    except (ValueError, TypeError):
        return 31536000


def validate_auth_config() -> None:
    """
    Validates mandatory authentication configuration at startup.
    Fails loudly with RuntimeError if required secrets are absent.
    """
    # 1. Enforce JWT_SECRET existence
    secret = get_jwt_secret()

    # 2. Check minimal recommended entropy length (32 bytes)
    if len(secret.encode("utf-8")) < 32:
        import warnings
        warnings.warn(
            "JWT_SECRET is shorter than 32 bytes (256 bits). "
            "Use a higher-entropy secret in production environments.",
            UserWarning,
            stacklevel=2
        )