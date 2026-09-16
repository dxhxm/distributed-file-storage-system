"""
app.api package initialization.
Exports route modules for registration in the main application.
"""

from app.api import auth, consensus, health, replicate_routes, time_sync

__all__ = ["auth", "consensus", "health", "replicate_routes", "time_sync"]
