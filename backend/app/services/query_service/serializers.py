"""Build the public QueryResponse from the agent's final state."""

from __future__ import annotations

from app.agents.state import AgentState
from app.schemas.query import (
    CorrectionStep,
    QueryResponse,
    ResultMetadata,
    RetrievalDisclosure,
    RetrievedTableHint,
)
from app.services.query_service.context import QueryContext
from app.services.retrieval_service import RetrievalResult
from app.services.visualization_service import VisualizationHint, recommend


def build_response(
    state: AgentState, ctx: QueryContext, request_id: str, max_viz_rows: int
) -> QueryResponse:
    columns = state.get("execution_columns", [])
    rows = state.get("execution_rows", [])
    return QueryResponse(
        answer=state.get("natural_language_answer", ""),
        sql=state.get("final_sql") or state.get("generated_sql", ""),
        explanation=state.get("sql_explanation", ""),
        results=rows,
        columns=columns,
        row_count=state.get("execution_row_count", 0),
        execution_time_ms=state.get("execution_time_ms", 0.0),
        visualization=_viz_for(columns, rows, max_viz_rows),
        metadata=ResultMetadata(
            retry_count=state.get("retry_count", 0),
            input_tokens=state.get("input_tokens", 0),
            output_tokens=state.get("output_tokens", 0),
            llm_provider=state.get("llm_provider", ""),
            truncated=state.get("execution_truncated", False),
            request_id=request_id,
            failed_stage=state.get("validation_stage")
            if state.get("execution_error") or state.get("validation_errors")
            else None,
            corrections=[
                CorrectionStep(
                    attempt=a["attempt"],
                    failed_sql=a.get("failed_sql", ""),
                    error=a.get("error", ""),
                )
                for a in state.get("correction_history", [])
            ],
            retrieval=_retrieval_disclosure(ctx.retrieval),
        ),
    )


def _retrieval_disclosure(retrieval: RetrievalResult) -> RetrievalDisclosure:
    return RetrievalDisclosure(
        tables=[
            RetrievedTableHint(
                name=t.name, score=t.score, via=t.via, lexical=t.lexical, vector=t.vector
            )
            for t in retrieval.tables
        ],
        schema_tokens=retrieval.token_estimate,
    )


def _viz_for(columns: list[str], rows: list[dict], cap: int) -> VisualizationHint:
    if len(rows) > cap:
        return VisualizationHint(chart="table", reason="Row count exceeds visualization cap")
    return recommend(columns, rows)
