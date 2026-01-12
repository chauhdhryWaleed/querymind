"""Auth dependencies: service wiring, current session/user/workspace, ENC_KEY, and CSRF."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_redis
from app.config.settings import Settings, get_settings
from app.database.session import get_rw_session
from app.models.session import UserSession
from app.models.user import User
from app.models.workspace import Workspace
from app.security import sessions as sess
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.connection_service import ConnectionService
from app.services.email_service import EmailService
from app.services.llm_key_service import LlmKeyService


def get_audit_service(
    db: Annotated[AsyncSession, Depends(get_rw_session)],
) -> AuditService:
    return AuditService(db)


def get_email_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmailService:
    return EmailService(settings, arq_pool=getattr(request.app.state, "arq", None))


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    redis: Annotated[Redis, Depends(get_redis)],
    settings: Annotated[Settings, Depends(get_settings)],
    email: Annotated[EmailService, Depends(get_email_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> AuthService:
    return AuthService(db, redis, settings, email, audit)


_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


async def current_session(
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    session_cookie: Annotated[str | None, Cookie(alias=sess.SESSION_COOKIE)] = None,
) -> UserSession:
    if not session_cookie:
        raise _UNAUTH
    try:
        import uuid

        sid = uuid.UUID(session_cookie)
    except (ValueError, TypeError):
        raise _UNAUTH from None
    session = await db.get(UserSession, sid)
    if session is None or session.expires_at <= datetime.now(UTC):
        raise _UNAUTH
    return session


async def current_user(
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    session: Annotated[UserSession, Depends(current_session)],
) -> User:
    user = await db.get(User, session.user_id)
    if user is None:
        raise _UNAUTH
    return user


async def current_workspace(
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    user: Annotated[User, Depends(current_user)],
) -> Workspace:
    from sqlalchemy import select

    ws = await db.scalar(select(Workspace).where(Workspace.owner_user_id == user.id).limit(1))
    if ws is None:
        raise _UNAUTH
    return ws


async def get_enc_key(
    redis: Annotated[Redis, Depends(get_redis)],
    session: Annotated[UserSession, Depends(current_session)],
) -> bytes:
    """The session's AES key. Absent ⇒ session expired in Redis ⇒ re-login."""
    key = await sess.get_enc_key(redis, str(session.id))
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Encryption key unavailable; please log in again.",
        )
    return key


async def require_csrf(
    session: Annotated[UserSession, Depends(current_session)],
    x_csrf_token: Annotated[str | None, Header(alias=sess.CSRF_HEADER)] = None,
) -> None:
    """Enforce the double-submit CSRF token on state-changing requests."""
    if not x_csrf_token or not sess.constant_time_equals(session.csrf_token, x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing CSRF token"
        )


def get_connection_service(
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    enc_key: Annotated[bytes, Depends(get_enc_key)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> ConnectionService:
    return ConnectionService(db, enc_key, audit)


def get_llm_key_service(
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    enc_key: Annotated[bytes, Depends(get_enc_key)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> LlmKeyService:
    return LlmKeyService(db, enc_key, audit)
