"""Orchestrates one QueryMind request: runs the LangGraph agent, persists the
run, and (when streaming) emits each node update as an SSE stage event."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dependencies import AgentDeps
from app.agents.graph import build_graph
from app.agents.state import AgentState
from app.config.settings import Settings
from app.executors.sql_executor import SqlExecutor
from app.llm.base import LLMProvider
from app.memory.conversation import ConversationMemory, make_conversation_turn
from app.models.history import QueryHistory
from app.schemas.query import QueryRequest, QueryResponse
from app.services.history_service import HistoryService
from app.services.query_service.context import QueryContext
from app.services.query_service.serializers import build_response
from app.services.query_service.streaming import STAGE_LABEL, sse_event, stage_payload
from app.validators.pipeline import ValidationPipeline

log = structlog.get_logger(__name__)


class QueryService:
    def __init__(
        self,
        *,
        user_session: AsyncSession,
        rw_session: AsyncSession,
        llm: LLMProvider,
        executor: SqlExecutor,
        validation_pipeline: ValidationPipeline,
        conversation_memory: ConversationMemory,
        settings: Settings,
        request_id: str,
        context: QueryContext,
        arq_pool: Any | None = None,
    ) -> None:
        self._rw_session = rw_session
        self._settings = settings
        self._request_id = request_id
        self._history = HistoryService(rw_session)
        self._memory = conversation_memory
        self._ctx = context
        self._arq = arq_pool
        self._deps = AgentDeps(
            llm=llm,
            executor=executor,
            validation_pipeline=validation_pipeline,
            ro_session=user_session,
            settings=settings,
        )

    async def run(self, request: QueryRequest) -> QueryResponse:
        session_id = request.session_id or str(uuid.uuid4())
        history = await self._memory.get_history(session_id)
        initial = self._initial_state(request.question, session_id, history)

        graph = build_graph(self._deps)
        final_state: AgentState = await graph.ainvoke(initial)

        await self._persist(session_id, final_state)
        return build_response(
            final_state, self._ctx, self._request_id, self._settings.MAX_VISUALIZABLE_ROWS
        )

    async def stream(self, request: QueryRequest) -> AsyncGenerator[str, None]:
        """Emit pipeline events for the UI: a `meta` event, one `stage` per
        LangGraph node, then a terminal `result` or `error`."""
        session_id = request.session_id or str(uuid.uuid4())
        history = await self._memory.get_history(session_id)
        initial = self._initial_state(request.question, session_id, history)

        yield sse_event("meta", {"session_id": session_id, "request_id": self._request_id})
        # Retrieval runs before the stream opens (pre-seeded into state), so the
        # in-graph schema node is a no-op; surface it explicitly as the first stage.
        yield sse_event(
            "stage",
            {
                "node": "schema",
                "label": STAGE_LABEL["schema"],
                "payload": {"table_count": len(self._ctx.retrieval.tables)},
            },
        )

        graph = build_graph(self._deps)
        final_state: dict[str, Any] = dict(initial)

        try:
            async for chunk in graph.astream(initial, stream_mode="updates"):
                for node_name, delta in chunk.items():
                    if not isinstance(delta, dict) or not delta:
                        continue
                    final_state.update(delta)
                    yield sse_event(
                        "stage",
                        {
                            "node": node_name,
                            "label": STAGE_LABEL.get(node_name, node_name),
                            "payload": stage_payload(node_name, delta),
                        },
                    )
        except Exception as exc:
            log.exception("query.stream.error", request_id=self._request_id)
            yield sse_event("error", {"message": str(exc)})
            return

        await self._persist(session_id, final_state)  # type: ignore[arg-type]
        response = build_response(
            final_state,  # type: ignore[arg-type]
            self._ctx,
            self._request_id,
            self._settings.MAX_VISUALIZABLE_ROWS,
        )
        yield sse_event("result", response.model_dump(mode="json"))

    def _initial_state(self, question: str, session_id: str, history: list) -> AgentState:
        return AgentState(
            question=question,
            session_id=session_id,
            request_id=self._request_id,
            schema_context=self._ctx.retrieval.formatted_schema,
            raw_schema=self._ctx.retrieval.raw_schema,
            conversation_history=history,
            generated_sql="",
            sql_explanation="",
            validation_errors=[],
            validation_passed=False,
            validation_stage="",
            execution_rows=[],
            execution_columns=[],
            execution_row_count=0,
            execution_time_ms=0.0,
            execution_truncated=False,
            execution_error=None,
            retry_count=0,
            max_retries=self._settings.MAX_RETRIES,
            correction_history=[],
            input_tokens=0,
            output_tokens=0,
            llm_provider=self._ctx.llm_provider_name,
            final_sql="",
            natural_language_answer="",
            agent_error=None,
        )

    async def _persist(self, session_id: str, state: AgentState) -> None:
        succeeded = not state.get("execution_error") and bool(state.get("generated_sql"))
        final_sql = state.get("final_sql") or state.get("generated_sql", "")
        try:
            record = QueryHistory(
                workspace_id=self._ctx.workspace_id,
                user_id=self._ctx.user_id,
                connection_id=self._ctx.connection_id,
                llm_key_id=self._ctx.llm_key_id,
                session_id=session_id,
                request_id=self._request_id,
                question=state.get("question", ""),
                generated_sql=state.get("generated_sql", ""),
                final_sql=final_sql,
                answer=state.get("natural_language_answer") or None,
                retrieved_tables=[t.name for t in self._ctx.retrieval.tables],
                execution_time_ms=state.get("execution_time_ms", 0.0),
                row_count=state.get("execution_row_count", 0),
                retry_count=state.get("retry_count", 0),
                llm_provider=state.get("llm_provider", ""),
                input_tokens=state.get("input_tokens", 0),
                output_tokens=state.get("output_tokens", 0),
                error=state.get("agent_error") or state.get("execution_error"),
            )
            await self._history.save(record)
        except Exception:
            log.exception("query_service.history_persist_failed", request_id=self._request_id)

        if not succeeded:
            return

        try:
            turn = make_conversation_turn(
                question=state.get("question", ""),
                sql=final_sql,
                row_count=state.get("execution_row_count", 0),
                truncated=state.get("execution_truncated", False),
            )
            await self._memory.append_turn(session_id, turn)
        except Exception:
            log.exception("query_service.memory_persist_failed", request_id=self._request_id)

        # Reinforce FK-edge weights between joined tables (learning loop).
        if self._arq is not None and final_sql:
            try:
                await self._arq.enqueue_job(
                    "bump_fk_weights",
                    connection_id=str(self._ctx.connection_id),
                    sql=final_sql,
                )
            except Exception:
                log.warning("query_service.fk_weight_enqueue_failed", request_id=self._request_id)
