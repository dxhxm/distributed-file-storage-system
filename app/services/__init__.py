"""
app.services package initialization.
Exports core services for easy access across the application.
"""

from app.services.auth_service import hash_password, verify_password
from app.services.user_storage import (
    init_db,
    create_user,
    get_user_by_username,
    get_user_by_id,
    list_users,
    delete_user,
    get_db_path,
)
from app.services.jwt_service import (
    create_access_token,
    decode_access_token,
    JWTError,
    TokenExpiredError,
    TokenInvalidError,
    get_jwt_secret,
    get_jwt_algorithm,
)

__all__ = [
    "hash_password",
    "verify_password",
    "init_db",
    "create_user",
    "get_user_by_username",
    "get_user_by_id",
    "list_users",
    "delete_user",
    "get_db_path",
    "create_access_token",
    "decode_access_token",
    "JWTError",
    "TokenExpiredError",
    "TokenInvalidError",
    "get_jwt_secret",
    "get_jwt_algorithm",
]
