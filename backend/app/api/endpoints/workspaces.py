"""Workspace listing and rename. One workspace per user at MVP."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import current_user, require_csrf
from app.database.session import get_rw_session
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.auth import WorkspaceOut, WorkspacePreferencesUpdate, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _out(ws: Workspace, role: str) -> WorkspaceOut:
    return WorkspaceOut(
        id=ws.id,
        name=ws.name,
        role=role,
        default_model=ws.default_model,
        max_rows=ws.max_rows,
        statement_timeout_ms=ws.statement_timeout_ms,
    )


async def _role_for(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    return await db.scalar(
        select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )


async def _editable(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> str:
    """Return the caller's role, or raise 404/403. Only owner/editor may write."""
    role = await _role_for(db, workspace_id, user_id)
    if role is None:  # unknown / not a member ⇒ 404 (don't reveal existence)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if role not in ("owner", "editor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return role


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    user: Annotated[User, Depends(current_user)],
) -> list[WorkspaceOut]:
    rows = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    )
    return [_out(ws, role) for ws, role in rows.all()]


@router.patch("/{workspace_id}", response_model=WorkspaceOut, dependencies=[Depends(require_csrf)])
async def rename_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    user: Annotated[User, Depends(current_user)],
) -> WorkspaceOut:
    role = await _editable(db, workspace_id, user.id)
    ws = await db.get(Workspace, workspace_id)
    assert ws is not None  # role lookup guarantees membership
    ws.name = payload.name
    await db.commit()
    return _out(ws, role)


@router.patch(
    "/{workspace_id}/preferences",
    response_model=WorkspaceOut,
    dependencies=[Depends(require_csrf)],
)
async def update_preferences(
    workspace_id: uuid.UUID,
    payload: WorkspacePreferencesUpdate,
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    user: Annotated[User, Depends(current_user)],
) -> WorkspaceOut:
    role = await _editable(db, workspace_id, user.id)
    ws = await db.get(Workspace, workspace_id)
    assert ws is not None
    # Only touch fields the client explicitly sent (null clears; omitted is left as-is).
    fields = payload.model_dump(exclude_unset=True)
    if "default_model" in fields:
        model = (fields["default_model"] or "").strip()
        ws.default_model = model or None
    if "max_rows" in fields:
        ws.max_rows = fields["max_rows"]
    if "statement_timeout_ms" in fields:
        ws.statement_timeout_ms = fields["statement_timeout_ms"]
    await db.commit()
    return _out(ws, role)
