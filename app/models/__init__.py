"""
app.models package initialization.
Re-exports core models for convenient imports across the application.
"""

from app.models.user_model import Role, User

__all__ = ["Role", "User"]
