"""Per-request collaborators shared by the /query endpoints.

`QueryRuntime` resolves the target connection, BYOK key, and schema slice, then
builds a `QueryService` bound to a fresh read-only session on the user's database.
It is wired as a single FastAPI dependency so the route handlers stay thin.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import (
    current_user,
    current_workspace,
    get_connection_service,
    get_llm_key_service,
)
from app.api.dependencies import (
    get_arq,
    get_conversation_memory,
    get_embedder,
    get_executor,
    get_validation_pipeline,
)
from app.config.settings import Settings, get_settings
from app.database.session import get_rw_session
from app.database.user_db import user_db_session
from app.drivers import ConnectionCredentials
from app.executors.sql_executor import SqlExecutor
from app.llm.factory import build_llm_provider, default_model
from app.memory.conversation import ConversationMemory
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.query import QueryRequest
from app.services.connection_service import ConnectionService
from app.services.llm_key_service import LlmKeyService
from app.services.query_service import QueryContext, QueryService
from app.services.retrieval_service import RetrievalService


class LLMKeyRejected(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The LLM provider rejected this API key. Check the key in Settings.",
        )


def is_llm_auth_error(exc: BaseException) -> bool:
    """True when the exception is an LLM provider rejecting the BYOK key (401)."""
    name = type(exc).__name__
    msg = str(exc).lower()
    return name == "AuthenticationError" or "x-api-key" in msg or "invalid api key" in msg


@dataclass
class Prepared:
    creds: ConnectionCredentials
    read_only: bool
    provider: Any
    context: QueryContext


class QueryRuntime:
    def __init__(
        self,
        *,
        request: Request,
        db: AsyncSession,
        workspace: Workspace,
        user: User,
        conn_svc: ConnectionService,
        key_svc: LlmKeyService,
        embedder: Any,
        executor: SqlExecutor,
        pipeline: Any,
        memory: ConversationMemory,
        settings: Settings,
        arq: Any,
    ) -> None:
        self._request = request
        self._db = db
        self._workspace = workspace
        self._user = user
        self._conn_svc = conn_svc
        self._key_svc = key_svc
        self._embedder = embedder
        self._executor = executor
        self._pipeline = pipeline
        self._memory = memory
        self._settings = settings
        self._arq = arq

    async def prepare(self, body: QueryRequest) -> Prepared:
        conn = await self._resolve_connection(body.connection_id)
        key = await self._resolve_key(body.llm_key_id)

        api_key = self._key_svc.decrypt_api_key(key)
        model = (
            key.model_override
            or self._workspace.default_model
            or default_model(key.provider, self._settings)
        )
        provider = build_llm_provider(key.provider, api_key, model, self._settings.LLM_MAX_TOKENS)
        retrieval = await RetrievalService(self._db, self._embedder).retrieve(
            conn.id, body.question
        )
        context = QueryContext(
            workspace_id=self._workspace.id,
            user_id=self._user.id,
            connection_id=conn.id,
            llm_key_id=key.id,
            llm_provider_name=key.provider,
            retrieval=retrieval,
        )
        return Prepared(
            creds=self._conn_svc.credentials(conn),
            read_only=conn.read_only,
            provider=provider,
            context=context,
        )

    @asynccontextmanager
    async def service(self, prepared: Prepared) -> AsyncIterator[QueryService]:
        """Open the user-DB session and yield a QueryService for its lifetime."""
        async with user_db_session(prepared.creds, read_only=prepared.read_only) as us:
            yield QueryService(
                user_session=us,
                rw_session=self._db,
                llm=prepared.provider,
                executor=self._executor_for_workspace(),
                validation_pipeline=self._pipeline,
                conversation_memory=self._memory,
                settings=self._settings,
                request_id=self._request_id,
                context=prepared.context,
                arq_pool=self._arq,
            )

    async def _resolve_connection(self, connection_id: uuid.UUID):
        conn = await self._conn_svc.get(self._workspace.id, connection_id)
        if conn is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found"
            )
        if conn.index_status != "ready":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Schema not ready (status: {conn.index_status}). Reload the schema and retry."
                ),
            )
        return conn

    async def _resolve_key(self, llm_key_id: uuid.UUID | None):
        if llm_key_id is not None:
            key = await self._key_svc.get(self._workspace.id, llm_key_id)
            if key is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="LLM key not found"
                )
            return key
        key = await self._key_svc.get_default(self._workspace.id)
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No LLM key configured. Add one in Settings to run queries.",
            )
        return key

    def _executor_for_workspace(self) -> SqlExecutor:
        """Apply per-workspace row-cap / timeout overrides, falling back to the
        shared executor when the workspace sets neither."""
        ws, settings = self._workspace, self._settings
        if ws.max_rows is None and ws.statement_timeout_ms is None:
            return self._executor
        timeout = (
            ws.statement_timeout_ms / 1000
            if ws.statement_timeout_ms is not None
            else settings.QUERY_TIMEOUT_SECONDS
        )
        return SqlExecutor(max_rows=ws.max_rows or settings.MAX_ROWS, timeout_seconds=timeout)

    @property
    def _request_id(self) -> str:
        return getattr(self._request.state, "request_id", str(uuid.uuid4()))


def get_query_runtime(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_rw_session)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    user: Annotated[User, Depends(current_user)],
    conn_svc: Annotated[ConnectionService, Depends(get_connection_service)],
    key_svc: Annotated[LlmKeyService, Depends(get_llm_key_service)],
    embedder: Annotated[Any, Depends(get_embedder)],
    executor: Annotated[SqlExecutor, Depends(get_executor)],
    pipeline: Annotated[Any, Depends(get_validation_pipeline)],
    memory: Annotated[ConversationMemory, Depends(get_conversation_memory)],
    settings: Annotated[Settings, Depends(get_settings)],
    arq: Annotated[Any, Depends(get_arq)],
) -> QueryRuntime:
    return QueryRuntime(
        request=request,
        db=db,
        workspace=workspace,
        user=user,
        conn_svc=conn_svc,
        key_svc=key_svc,
        embedder=embedder,
        executor=executor,
        pipeline=pipeline,
        memory=memory,
        settings=settings,
        arq=arq,
    )
