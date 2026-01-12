"""LlmKeyService: encrypted CRUD for BYOK LLM API keys, with at most one default per workspace."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_key import LlmKey
from app.schemas.llm_key import LlmKeyCreate, LlmKeyOut, LlmKeyUpdate
from app.security import crypto
from app.services.audit_service import AuditService


def _hint(api_key: str) -> str:
    tail = api_key[-4:] if len(api_key) >= 4 else api_key
    return f"…{tail}"


class LlmKeyService:
    def __init__(self, db: AsyncSession, enc_key: bytes, audit: AuditService) -> None:
        self._db = db
        self._enc_key = enc_key
        self._audit = audit

    def _dek(self, key: LlmKey) -> bytes:
        return crypto.unwrap_dek(key.wrapped_dek, self._enc_key)

    def decrypt_api_key(self, key: LlmKey) -> str:
        return crypto.decrypt_str(key.api_key_encrypted, self._dek(key))

    def to_out(self, key: LlmKey) -> LlmKeyOut:
        return LlmKeyOut(
            id=key.id,
            provider=key.provider,
            label=key.label,
            model_override=key.model_override,
            is_default=key.is_default,
            key_hint=_hint(self.decrypt_api_key(key)),
            created_at=key.created_at,
        )

    async def _clear_defaults(self, workspace_id: uuid.UUID) -> None:
        await self._db.execute(
            sa_update(LlmKey)
            .where(LlmKey.workspace_id == workspace_id, LlmKey.is_default.is_(True))
            .values(is_default=False)
        )

    async def create(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, payload: LlmKeyCreate
    ) -> LlmKey:
        dek = crypto.generate_dek()
        if payload.is_default:
            await self._clear_defaults(workspace_id)
        key = LlmKey(
            workspace_id=workspace_id,
            provider=payload.provider,
            label=payload.label,
            wrapped_dek=crypto.wrap_dek(dek, self._enc_key),
            api_key_encrypted=crypto.encrypt_str(payload.api_key, dek),
            model_override=payload.model_override,
            is_default=payload.is_default,
        )
        self._db.add(key)
        await self._db.flush()
        await self._audit.record(
            "llm_key.create",
            user_id=user_id,
            workspace_id=workspace_id,
            payload={"llm_key_id": str(key.id), "provider": key.provider},
        )
        await self._db.commit()
        await self._db.refresh(key)
        return key

    async def list(self, workspace_id: uuid.UUID) -> list[LlmKey]:
        rows = await self._db.scalars(
            select(LlmKey)
            .where(LlmKey.workspace_id == workspace_id)
            .order_by(LlmKey.created_at.desc())
        )
        return list(rows.all())

    async def get(self, workspace_id: uuid.UUID, key_id: uuid.UUID) -> LlmKey | None:
        key = await self._db.get(LlmKey, key_id)
        if key is None or key.workspace_id != workspace_id:
            return None
        return key

    async def get_default(self, workspace_id: uuid.UUID) -> LlmKey | None:
        """The workspace's default key, falling back to the most recent one."""
        default = await self._db.scalar(
            select(LlmKey).where(LlmKey.workspace_id == workspace_id, LlmKey.is_default.is_(True))
        )
        if default is not None:
            return default
        return await self._db.scalar(
            select(LlmKey)
            .where(LlmKey.workspace_id == workspace_id)
            .order_by(LlmKey.created_at.desc())
            .limit(1)
        )

    async def update(self, key: LlmKey, user_id: uuid.UUID, payload: LlmKeyUpdate) -> LlmKey:
        if payload.label is not None:
            key.label = payload.label
        if payload.model_override is not None:
            key.model_override = payload.model_override
        if payload.api_key is not None:
            key.api_key_encrypted = crypto.encrypt_str(payload.api_key, self._dek(key))
        if payload.is_default is True and not key.is_default:
            await self._clear_defaults(key.workspace_id)
            key.is_default = True
        elif payload.is_default is False:
            key.is_default = False
        await self._db.commit()
        await self._db.refresh(key)
        return key

    async def delete(self, key: LlmKey, user_id: uuid.UUID) -> None:
        await self._audit.record(
            "llm_key.delete",
            user_id=user_id,
            workspace_id=key.workspace_id,
            payload={"llm_key_id": str(key.id)},
        )
        await self._db.delete(key)
        await self._db.commit()
