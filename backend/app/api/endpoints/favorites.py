from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import current_user, current_workspace, require_csrf
from app.database.session import get_rw_session
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.favorites import FavoriteItem, FavoritesResponse, SaveFavoriteRequest
from app.services.favorites_service import FavoritesService

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=FavoritesResponse)
async def list_favorites(
    session: Annotated[AsyncSession, Depends(get_rw_session)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    limit: int = 100,
) -> FavoritesResponse:
    items = await FavoritesService(session).list(workspace.id, limit=limit)
    return FavoritesResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=FavoriteItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def save_favorite(
    payload: SaveFavoriteRequest,
    session: Annotated[AsyncSession, Depends(get_rw_session)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    user: Annotated[User, Depends(current_user)],
) -> FavoriteItem:
    return await FavoritesService(session).create(workspace.id, user.id, payload)


@router.delete(
    "/{favorite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_favorite(
    favorite_id: str,
    session: Annotated[AsyncSession, Depends(get_rw_session)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
) -> None:
    ok = await FavoritesService(session).delete(workspace.id, favorite_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Favorite not found")
