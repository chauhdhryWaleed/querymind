"""Shared state, value objects, and helpers for the auth service mixins."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.models.session import UserSession
from app.models.user import EmailToken, User
from app.models.workspace import Workspace
from app.security import sessions as sess
from app.security.passwords import hash_password
from app.services.audit_service import AuditService
from app.services.email_service import EmailService

# Throwaway hash so login of a non-existent user still spends verification time,
# closing the timing side-channel that would otherwise reveal which emails exist.
_DUMMY_HASH = hash_password("timing-equalizer")
_RESET_TTL = timedelta(hours=1)


def _now() -> datetime:
    return datetime.now(UTC)


class EmailTakenError(Exception):
    """Registration failed because the email is already in use."""


@dataclass
class SessionTokens:
    session_id: str
    refresh_token: str
    csrf_token: str


@dataclass
class AuthResult:
    user: User
    workspace: Workspace
    tokens: SessionTokens


class AuthBase:
    """Holds shared dependencies and helpers used by every auth mixin."""

    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        settings: Settings,
        email: EmailService,
        audit: AuditService,
    ) -> None:
        self._db = db
        self._redis = redis
        self._settings = settings
        self._email = email
        self._audit = audit

    async def _load_session(self, session_id: str) -> UserSession | None:
        try:
            sid = uuid.UUID(session_id)
        except (ValueError, TypeError):
            return None
        return await self._db.get(UserSession, sid)

    async def _issue_email_token(self, user_id: uuid.UUID, purpose: str) -> str:
        raw = sess.new_token()
        self._db.add(
            EmailToken(
                user_id=user_id,
                purpose=purpose,
                token_hash=sess.hash_token(raw),
                expires_at=_now() + _RESET_TTL,
            )
        )
        return raw

    async def _owned_workspace_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        rows = await self._db.scalars(
            select(Workspace.id).where(Workspace.owner_user_id == user_id)
        )
        return list(rows.all())
