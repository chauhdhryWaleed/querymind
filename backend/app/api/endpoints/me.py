"""GET /me: the current user and their workspaces."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import current_user, get_auth_service, require_csrf
from app.database.session import get_rw_session
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.auth import MeResponse, ProfileUpdate, UserOut, WorkspaceOut
from app.services.auth_service import AuthService

router = APIRouter(tags=["me"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        first_name=user.first_name,
        last_name=user.last_name,
        job_role=user.job_role,
        company=user.company,
        country=user.country,
        use_case=user.use_case,
        email_verified=user.email_verified_at is not None,
        created_at=user.created_at,
    )


def _workspace_out(ws: Workspace, role: str) -> WorkspaceOut:
    return WorkspaceOut(
        id=ws.id,
        name=ws.name,
        role=role,
        default_model=ws.default_model,
        max_rows=ws.max_rows,
        statement_timeout_ms=ws.statement_timeout_ms,
    )


@router.get("/me", response_model=MeResponse)
async def me(
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    user: Annotated[User, Depends(current_user)],
) -> MeResponse:
    rows = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    )
    workspaces = [_workspace_out(ws, role) for ws, role in rows.all()]
    return MeResponse(user=_user_out(user), workspaces=workspaces)


@router.patch("/me", response_model=UserOut, dependencies=[Depends(require_csrf)])
async def update_me(
    payload: ProfileUpdate,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    user: Annotated[User, Depends(current_user)],
) -> UserOut:
    updated = await auth.update_profile(user, payload.model_dump(exclude_unset=True))
    return _user_out(updated)
