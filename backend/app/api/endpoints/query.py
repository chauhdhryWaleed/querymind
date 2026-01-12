"""POST /query, /query/stream, /query/export.

Each call targets a user Connection plus BYOK key, retrieves the relevant schema
slice, and runs the agent against the user's own database over a fresh read-only
connection. Shared setup lives in `query_runtime.QueryRuntime`.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse

from app.api.auth_deps import require_csrf
from app.api.endpoints.query_runtime import (
    LLMKeyRejected,
    QueryRuntime,
    get_query_runtime,
    is_llm_auth_error,
)
from app.schemas.query import QueryRequest, QueryResponse
from app.services.export_service import to_csv, to_json
from app.services.query_service import QueryService

router = APIRouter(tags=["query"])

_Runtime = Annotated[QueryRuntime, Depends(get_query_runtime)]


async def _run_or_raise(svc: QueryService, body: QueryRequest) -> QueryResponse:
    try:
        return await svc.run(body)
    except Exception as exc:
        if is_llm_auth_error(exc):
            raise LLMKeyRejected() from exc
        raise


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(require_csrf)])
async def post_query(body: QueryRequest, runtime: _Runtime) -> QueryResponse:
    prepared = await runtime.prepare(body)
    async with runtime.service(prepared) as svc:
        return await _run_or_raise(svc, body)


@router.post("/query/stream", dependencies=[Depends(require_csrf)])
async def post_query_stream(body: QueryRequest, runtime: _Runtime) -> StreamingResponse:
    prepared = await runtime.prepare(body)

    async def _gen():
        async with runtime.service(prepared) as svc:
            async for event in svc.stream(body):
                yield event

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/query/export", dependencies=[Depends(require_csrf)])
async def post_query_export(
    body: QueryRequest,
    runtime: _Runtime,
    fmt: Annotated[Literal["csv", "json"], Query()],
) -> Response:
    prepared = await runtime.prepare(body)
    async with runtime.service(prepared) as svc:
        result = await _run_or_raise(svc, body)

    if not result.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query produced no executable result to export",
        )
    if fmt == "csv":
        return Response(
            content=to_csv(result.columns, result.results),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="results.csv"'},
        )
    return Response(
        content=to_json(result.columns, result.results),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="results.json"'},
    )
