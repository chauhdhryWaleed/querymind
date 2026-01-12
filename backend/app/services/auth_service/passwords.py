"""Password-reset flow: token issuance, redemption, and re-keying."""

from __future__ import annotations

from sqlalchemy import select

from app.models.session import UserSession
from app.models.user import EmailToken, User
from app.security import crypto
from app.security import sessions as sess
from app.security.passwords import hash_password
from app.services.auth_service.base import AuthBase, _now


class PasswordResetMixin(AuthBase):
    async def request_password_reset(self, email: str) -> str | None:
        """Issue a reset token and email it, returning the raw token.

        Behaves identically whether or not the email exists, to avoid user
        enumeration. Returns None only to the trusted caller (job/tests).
        """
        email = email.strip().lower()
        user = await self._db.scalar(select(User).where(User.email == email))
        if user is None:
            return None
        token = await self._issue_email_token(user.id, "reset")
        await self._audit.record("auth.password_reset_request", user_id=user.id)
        await self._db.commit()
        await self._email.send_password_reset(email, token)
        return token

    async def complete_password_reset(self, token: str, new_password: str) -> bool:
        token_hash = sess.hash_token(token)
        row = await self._db.scalar(
            select(EmailToken).where(
                EmailToken.token_hash == token_hash,
                EmailToken.purpose == "reset",
            )
        )
        if row is None or row.consumed_at is not None or row.expires_at <= _now():
            return False

        user = await self._db.get(User, row.user_id)
        if user is None:
            return False

        # A new password yields a new ENC_KEY, so previously encrypted credentials
        # are intentionally unrecoverable. Rotate the KDF salt and force re-login.
        user.password_hash = hash_password(new_password)
        user.kdf_salt = crypto.generate_kdf_salt()
        row.consumed_at = _now()

        existing = await self._db.scalars(select(UserSession).where(UserSession.user_id == user.id))
        for s in existing.all():
            await sess.delete_enc_key(self._redis, str(s.id))
            await self._db.delete(s)

        await self._audit.record("auth.password_reset_complete", user_id=user.id)
        await self._db.commit()
        return True
