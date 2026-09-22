"""
app.api package initialization.
Exports route modules and security dependencies for registration in the main application.
"""

from app.api import auth, consensus, health, replicate_routes, time_sync
from app.api.dependencies import (
    AuthenticatedUser,
    get_current_user,
    require_admin,
    require_human_user,
    require_role,
    require_system,
    require_user,
)

__all__ = [
    "auth",
    "consensus",
    "health",
    "replicate_routes",
    "time_sync",
    "AuthenticatedUser",
    "get_current_user",
    "require_admin",
    "require_human_user",
    "require_role",
    "require_system",
    "require_user",
]

