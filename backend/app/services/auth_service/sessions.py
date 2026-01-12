"""Session lifecycle: creation, refresh-token rotation, and revocation."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select

from app.models.session import UserSession
from app.security import sessions as sess
from app.services.auth_service.base import AuthBase, SessionTokens, _now


class SessionMixin(AuthBase):
    async def _create_session(
        self, user_id: uuid.UUID, enc_key: bytes, user_agent: str | None, ip: str | None
    ) -> SessionTokens:
        refresh_token = sess.new_token()
        csrf_token = sess.new_csrf_token()
        session = UserSession(
            user_id=user_id,
            refresh_token_hash=sess.hash_token(refresh_token),
            csrf_token=csrf_token,
            expires_at=_now() + timedelta(seconds=self._settings.REFRESH_TTL),
            user_agent=user_agent,
            ip=ip,
        )
        self._db.add(session)
        await self._db.flush()

        session_id = str(session.id)
        await sess.store_enc_key(self._redis, session_id, enc_key, ttl=self._settings.SESSION_TTL)
        return SessionTokens(
            session_id=session_id, refresh_token=refresh_token, csrf_token=csrf_token
        )

    async def logout(self, session_id: str) -> None:
        session = await self._load_session(session_id)
        if session is not None:
            await self._audit.record("auth.logout", user_id=session.user_id)
            await self._db.delete(session)
            await self._db.commit()
        await sess.delete_enc_key(self._redis, session_id)

    async def refresh(self, session_id: str, refresh_token: str) -> tuple[str, str] | None:
        """Rotate the refresh and CSRF tokens, returning the new pair.

        Returns None when the session or token is invalid so the caller can clear
        cookies. A token mismatch is treated as theft and kills the session.
        """
        session = await self._load_session(session_id)
        if session is None or session.expires_at <= _now():
            return None
        if not sess.constant_time_equals(
            session.refresh_token_hash, sess.hash_token(refresh_token)
        ):
            await self._db.delete(session)
            await self._db.commit()
            await sess.delete_enc_key(self._redis, session_id)
            return None

        new_refresh = sess.new_token()
        session.refresh_token_hash = sess.hash_token(new_refresh)
        session.csrf_token = sess.new_csrf_token()
        session.expires_at = _now() + timedelta(seconds=self._settings.REFRESH_TTL)
        await self._db.commit()
        await self._redis.expire(f"enckey:{session_id}", self._settings.SESSION_TTL)
        return new_refresh, session.csrf_token

    async def list_sessions(self, user_id: uuid.UUID) -> list[UserSession]:
        rows = await self._db.scalars(
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.expires_at > _now())
            .order_by(UserSession.created_at.desc())
        )
        return list(rows.all())

    async def revoke_session(self, user_id: uuid.UUID, session_id: str) -> bool:
        session = await self._load_session(session_id)
        if session is None or session.user_id != user_id:
            return False
        await sess.delete_enc_key(self._redis, str(session.id))
        await self._db.delete(session)
        await self._audit.record("auth.session_revoke", user_id=user_id)
        await self._db.commit()
        return True
