"""Workspace-scoped connection CRUD plus a connectivity test; mutations require CSRF."""

from __future__ import annotations

import dataclasses
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth_deps import (
    current_user,
    current_workspace,
    get_connection_service,
    require_csrf,
)
from app.api.dependencies import get_arq
from app.config.settings import Settings, get_settings
from app.models.connection import Connection
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionOut,
    ConnectionTestResponse,
    ConnectionUpdate,
    IndexedSchemaOut,
)
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/connections", tags=["connections"])

# Display name used to make the one-click demo connection idempotent per workspace.
DEMO_CONNECTION_NAME = "Demo database"


async def _require(svc: ConnectionService, workspace: Workspace, conn_id: uuid.UUID) -> Connection:
    conn = await svc.get(workspace.id, conn_id)
    if conn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return conn


async def _enqueue_index(arq, svc: ConnectionService, conn: Connection) -> None:
    """Queue background schema indexing. No-op (stays 'pending') without a pool."""
    if arq is None:
        return
    creds = dataclasses.asdict(svc.credentials(conn))
    await arq.enqueue_job("index_connection_schema", connection_id=str(conn.id), creds=creds)


@router.get("", response_model=list[ConnectionOut])
async def list_connections(
    svc: Annotated[ConnectionService, Depends(get_connection_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
) -> list[ConnectionOut]:
    return [svc.to_out(c) for c in await svc.list(workspace.id)]


@router.post(
    "",
    response_model=ConnectionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_connection(
    payload: ConnectionCreate,
    svc: Annotated[ConnectionService, Depends(get_connection_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    user: Annotated[User, Depends(current_user)],
    arq: Annotated[object, Depends(get_arq)],
) -> ConnectionOut:
    conn = await svc.create(workspace.id, user.id, payload)
    await _enqueue_index(arq, svc, conn)
    return svc.to_out(conn)


@router.post(
    "/demo",
    response_model=ConnectionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_demo_connection(
    svc: Annotated[ConnectionService, Depends(get_connection_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    user: Annotated[User, Depends(current_user)],
    arq: Annotated[object, Depends(get_arq)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConnectionOut:
    """One-click add the seeded read-only `demo` database; idempotent if one exists."""
    if not settings.DEMO_DB_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demo database is not available"
        )
    for existing in await svc.list(workspace.id):
        if existing.name == DEMO_CONNECTION_NAME:
            return svc.to_out(existing)

    payload = ConnectionCreate(
        name=DEMO_CONNECTION_NAME,
        dialect="postgres",
        host=settings.demo_db_host,
        port=settings.demo_db_port,
        database=settings.DEMO_DB_NAME,
        username=settings.DEMO_DB_USER,
        password=settings.DEMO_DB_PASSWORD,
        read_only=True,
    )
    conn = await svc.create(workspace.id, user.id, payload)
    await _enqueue_index(arq, svc, conn)
    return svc.to_out(conn)


@router.get("/{connection_id}", response_model=ConnectionOut)
async def get_connection(
    connection_id: uuid.UUID,
    svc: Annotated[ConnectionService, Depends(get_connection_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
) -> ConnectionOut:
    return svc.to_out(await _require(svc, workspace, connection_id))


@router.patch(
    "/{connection_id}", response_model=ConnectionOut, dependencies=[Depends(require_csrf)]
)
async def update_connection(
    connection_id: uuid.UUID,
    payload: ConnectionUpdate,
    svc: Annotated[ConnectionService, Depends(get_connection_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    user: Annotated[User, Depends(current_user)],
) -> ConnectionOut:
    conn = await _require(svc, workspace, connection_id)
    return svc.to_out(await svc.update(conn, user.id, payload))


@router.delete(
    "/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_connection(
    connection_id: uuid.UUID,
    svc: Annotated[ConnectionService, Depends(get_connection_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    user: Annotated[User, Depends(current_user)],
) -> None:
    conn = await _require(svc, workspace, connection_id)
    await svc.delete(conn, user.id)


@router.post(
    "/{connection_id}/test",
    response_model=ConnectionTestResponse,
    dependencies=[Depends(require_csrf)],
)
async def test_connection(
    connection_id: uuid.UUID,
    svc: Annotated[ConnectionService, Depends(get_connection_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
) -> ConnectionTestResponse:
    conn = await _require(svc, workspace, connection_id)
    result = await svc.test(conn)
    return ConnectionTestResponse(
        ok=result.ok,
        message=result.message,
        server_version=result.server_version,
        latency_ms=result.latency_ms,
    )


@router.post(
    "/{connection_id}/reload-schema",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def reload_schema(
    connection_id: uuid.UUID,
    svc: Annotated[ConnectionService, Depends(get_connection_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    arq: Annotated[object, Depends(get_arq)],
) -> dict:
    conn = await _require(svc, workspace, connection_id)
    await _enqueue_index(arq, svc, conn)
    return {"status": "queued", "connection_id": str(conn.id)}


@router.get("/{connection_id}/schema", response_model=IndexedSchemaOut)
async def get_schema(
    connection_id: uuid.UUID,
    svc: Annotated[ConnectionService, Depends(get_connection_service)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
) -> IndexedSchemaOut:
    conn = await _require(svc, workspace, connection_id)
    return await svc.get_indexed_schema(conn)
