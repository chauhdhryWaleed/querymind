"""Authentication service: registration, login, sessions, and account management."""

from __future__ import annotations

from app.services.auth_service.base import AuthResult, EmailTakenError, SessionTokens
from app.services.auth_service.service import AuthService

__all__ = ["AuthResult", "AuthService", "EmailTakenError", "SessionTokens"]
