"""BYOK LLM key management. Workspace-scoped; mutations require CSRF."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth_deps import (
    current_user,
    current_workspace,
    get_llm_key_service,
    require_csrf,
)
from app.models.llm_key import LlmKey
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.llm_key import LlmKeyCreate, LlmKeyOut, LlmKeyUpdate
from app.services.llm_key_service import LlmKeyService

router = APIRouter(prefix="/llm-keys", tags=["llm-keys"])


async def _require(svc: LlmKeyService, workspace: Workspace, key_id: uuid.UUID) -> LlmKey:
    key = await svc.get(workspace.id, key_id)
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM key not found")
    return key


@router.get("", response_model=list[LlmKeyOut])
async def list_keys(
    svc: Annotated[LlmKeyService, Depends(get_llm_key_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
) -> list[LlmKeyOut]:
    return [svc.to_out(k) for k in await svc.list(workspace.id)]


@router.post(
    "",
    response_model=LlmKeyOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_key(
    payload: LlmKeyCreate,
    svc: Annotated[LlmKeyService, Depends(get_llm_key_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    user: Annotated[User, Depends(current_user)],
) -> LlmKeyOut:
    return svc.to_out(await svc.create(workspace.id, user.id, payload))


@router.patch("/{key_id}", response_model=LlmKeyOut, dependencies=[Depends(require_csrf)])
async def update_key(
    key_id: uuid.UUID,
    payload: LlmKeyUpdate,
    svc: Annotated[LlmKeyService, Depends(get_llm_key_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    user: Annotated[User, Depends(current_user)],
) -> LlmKeyOut:
    key = await _require(svc, workspace, key_id)
    return svc.to_out(await svc.update(key, user.id, payload))


@router.delete(
    "/{key_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)]
)
async def delete_key(
    key_id: uuid.UUID,
    svc: Annotated[LlmKeyService, Depends(get_llm_key_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    user: Annotated[User, Depends(current_user)],
) -> None:
    key = await _require(svc, workspace, key_id)
    await svc.delete(key, user.id)
