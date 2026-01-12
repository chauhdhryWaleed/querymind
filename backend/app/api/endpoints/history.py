"""Workspace-scoped query history and Redis conversation reset."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import current_workspace, require_csrf
from app.api.dependencies import get_conversation_memory
from app.database.session import get_rw_session
from app.memory.conversation import ConversationMemory
from app.models.workspace import Workspace
from app.schemas.history import HistoryResponse
from app.services.history_service import HistoryService

router = APIRouter()


@router.get("/history", response_model=HistoryResponse, tags=["history"])
async def list_history(
    session: Annotated[AsyncSession, Depends(get_rw_session)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    connection_id: str | None = None,
    limit: int = 50,
) -> HistoryResponse:
    """Recent queries for the workspace, optionally filtered to one connection."""
    items = await HistoryService(session).list_recent(workspace.id, connection_id, limit=limit)
    return HistoryResponse(session_id=None, turns=items, total=len(items))


@router.delete(
    "/history",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["history"],
    dependencies=[Depends(require_csrf)],
)
async def clear_all_history(
    session: Annotated[AsyncSession, Depends(get_rw_session)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    connection_id: str | None = None,
) -> None:
    await HistoryService(session).clear(workspace.id, connection_id)


@router.delete(
    "/history/item/{history_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["history"],
    dependencies=[Depends(require_csrf)],
)
async def delete_history_item(
    history_id: str,
    session: Annotated[AsyncSession, Depends(get_rw_session)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
) -> None:
    ok = await HistoryService(session).delete_item(workspace.id, history_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History item not found")


@router.get("/history/{session_id}", response_model=HistoryResponse, tags=["history"])
async def get_history(
    session_id: str,
    session: Annotated[AsyncSession, Depends(get_rw_session)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    limit: int = 50,
) -> HistoryResponse:
    items = await HistoryService(session).get_by_session(workspace.id, session_id, limit=limit)
    return HistoryResponse(session_id=session_id, turns=items, total=len(items))


@router.delete(
    "/history/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["history"],
    dependencies=[Depends(require_csrf)],
)
async def clear_history(
    session_id: str,
    memory: Annotated[ConversationMemory, Depends(get_conversation_memory)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
) -> None:
    """Reset the multi-turn Redis conversation buffer for this session."""
    await memory.clear(session_id)
