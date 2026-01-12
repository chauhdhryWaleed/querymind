"""AuthService: registration and login, composed from the auth mixins.

Derives the password-based ENC_KEY at login and parks it in Redis for the session.
"""

from __future__ import annotations

from sqlalchemy import select

from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.security import crypto
from app.security.passwords import hash_password, verify_password
from app.services.auth_service.accounts import AccountMixin
from app.services.auth_service.base import _DUMMY_HASH, AuthResult, EmailTakenError
from app.services.auth_service.passwords import PasswordResetMixin
from app.services.auth_service.sessions import SessionMixin


class AuthService(SessionMixin, PasswordResetMixin, AccountMixin):
    async def register(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        job_role: str,
        company: str,
        country: str,
        use_case: str,
        user_agent: str | None,
        ip: str | None,
    ) -> AuthResult:
        """Create a user and their personal workspace, raising EmailTakenError if
        the email is taken."""
        email = email.strip().lower()
        first_name, last_name = first_name.strip(), last_name.strip()

        if await self._db.scalar(select(User).where(User.email == email)):
            raise EmailTakenError

        kdf_salt = crypto.generate_kdf_salt()
        user = User(
            email=email,
            name=f"{first_name} {last_name}".strip() or None,
            first_name=first_name or None,
            last_name=last_name or None,
            job_role=job_role.strip() or None,
            company=company.strip() or None,
            country=country.strip() or None,
            use_case=use_case.strip() or None,
            password_hash=hash_password(password),
            kdf_salt=kdf_salt,
        )
        self._db.add(user)
        await self._db.flush()

        workspace = Workspace(owner_user_id=user.id, name="My Workspace")
        self._db.add(workspace)
        await self._db.flush()
        self._db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))

        enc_key = crypto.derive_enc_key(password, kdf_salt)
        tokens = await self._create_session(user.id, enc_key, user_agent, ip)

        await self._audit.record("auth.register", user_id=user.id, workspace_id=workspace.id)
        await self._db.commit()

        # Verification email is best-effort; login is allowed immediately.
        token = await self._issue_email_token(user.id, "verify")
        await self._email.send_verification(email, token)
        await self._db.commit()

        await self._db.refresh(user)
        await self._db.refresh(workspace)
        return AuthResult(user=user, workspace=workspace, tokens=tokens)

    async def login(
        self, email: str, password: str, *, user_agent: str | None, ip: str | None
    ) -> AuthResult | None:
        email = email.strip().lower()
        user = await self._db.scalar(select(User).where(User.email == email))
        if user is None:
            verify_password(_DUMMY_HASH, password)  # equalize timing
            return None
        if not verify_password(user.password_hash, password):
            return None

        workspace = await self._db.scalar(
            select(Workspace).where(Workspace.owner_user_id == user.id).limit(1)
        )
        if workspace is None:
            return None

        enc_key = crypto.derive_enc_key(password, user.kdf_salt)
        tokens = await self._create_session(user.id, enc_key, user_agent, ip)
        await self._audit.record("auth.login", user_id=user.id, workspace_id=workspace.id)
        await self._db.commit()
        return AuthResult(user=user, workspace=workspace, tokens=tokens)
