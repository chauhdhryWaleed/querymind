"""Authenticated account management: password change, profile, deletion."""

from __future__ import annotations

import uuid

from cryptography.exceptions import InvalidTag
from sqlalchemy import select

from app.models.connection import Connection
from app.models.llm_key import LlmKey
from app.models.session import UserSession
from app.models.user import User
from app.security import crypto
from app.security import sessions as sess
from app.security.passwords import hash_password, verify_password
from app.services.auth_service.base import AuthBase


class AccountMixin(AuthBase):
    async def change_password(
        self, user: User, current_password: str, new_password: str, *, keep_session_id: str
    ) -> bool:
        """Verify the current password, then re-wrap every stored credential.

        Unlike the reset flow, this re-keys each connection/LLM-key DEK from the
        old ENC_KEY to the new one so saved credentials survive. Other sessions are
        revoked; the calling session is kept and its Redis ENC_KEY refreshed.
        """
        if not verify_password(user.password_hash, current_password):
            return False

        old_enc = crypto.derive_enc_key(current_password, user.kdf_salt)
        new_salt = crypto.generate_kdf_salt()
        new_enc = crypto.derive_enc_key(new_password, new_salt)

        ws_ids = await self._owned_workspace_ids(user.id)
        if ws_ids:
            await self._rekey_credentials(ws_ids, old_enc, new_enc)

        user.password_hash = hash_password(new_password)
        user.kdf_salt = new_salt

        sessions = await self._db.scalars(select(UserSession).where(UserSession.user_id == user.id))
        for s in sessions.all():
            if str(s.id) == keep_session_id:
                await sess.store_enc_key(
                    self._redis, keep_session_id, new_enc, ttl=self._settings.SESSION_TTL
                )
            else:
                await sess.delete_enc_key(self._redis, str(s.id))
                await self._db.delete(s)

        await self._audit.record("auth.password_change", user_id=user.id)
        await self._db.commit()
        return True

    async def _rekey_credentials(
        self, ws_ids: list[uuid.UUID], old_enc: bytes, new_enc: bytes
    ) -> None:
        """Re-wrap connection and LLM-key DEKs from the old ENC_KEY to the new one.

        Credentials wrapped under a different owner's key fail to unwrap and are
        skipped rather than corrupted.
        """
        conns = await self._db.scalars(
            select(Connection).where(Connection.workspace_id.in_(ws_ids))
        )
        for conn in conns.all():
            try:
                dek = crypto.unwrap_dek(conn.wrapped_dek, old_enc)
            except InvalidTag:
                continue
            conn.wrapped_dek = crypto.wrap_dek(dek, new_enc)

        keys = await self._db.scalars(select(LlmKey).where(LlmKey.workspace_id.in_(ws_ids)))
        for key in keys.all():
            try:
                dek = crypto.unwrap_dek(key.wrapped_dek, old_enc)
            except InvalidTag:
                continue
            key.wrapped_dek = crypto.wrap_dek(dek, new_enc)

    async def update_profile(self, user: User, fields: dict) -> User:
        """Apply a partial profile update; `fields` holds only client-sent keys."""
        for key in ("first_name", "last_name", "job_role", "company", "country", "use_case"):
            if key in fields:
                setattr(user, key, (fields[key] or "").strip() or None)

        if "first_name" in fields or "last_name" in fields:
            full = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
            user.name = full or user.name

        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def resend_verification(self, user: User) -> bool:
        """Issue a fresh verify token and email it; no-op if already verified."""
        if user.email_verified_at is not None:
            return False
        token = await self._issue_email_token(user.id, "verify")
        await self._db.commit()
        await self._email.send_verification(user.email, token)
        return True

    async def delete_account(self, user: User) -> None:
        """Delete the user; FK cascades remove dependent rows. Redis ENC_KEYs are
        cleared first so no key material lingers in memory."""
        sessions = await self._db.scalars(select(UserSession).where(UserSession.user_id == user.id))
        for s in sessions.all():
            await sess.delete_enc_key(self._redis, str(s.id))
        await self._audit.record("auth.account_delete", user_id=user.id)
        await self._db.delete(user)
        await self._db.commit()
