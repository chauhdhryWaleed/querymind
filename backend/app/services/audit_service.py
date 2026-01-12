"""Append-only audit logging. Thin wrapper over the audit_log table."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        event_type: str,
        *,
        user_id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Add an audit row to the current transaction (caller commits)."""
        self._db.add(
            AuditLog(
                event_type=event_type,
                user_id=user_id,
                workspace_id=workspace_id,
                payload=payload,
            )
        )
