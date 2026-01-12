"""Stage 4: execute the validated SQL and capture results or error."""

from __future__ import annotations

import structlog

from app.agents.dependencies import AgentDeps
from app.agents.state import AgentState
from app.executors.sql_executor import QueryExecutionError, QueryTimeoutError

log = structlog.get_logger(__name__)


async def execute_node(state: AgentState, deps: AgentDeps) -> dict:
    sql = state["generated_sql"]

    try:
        result = await deps.executor.execute(sql, deps.ro_session)
    except QueryTimeoutError as exc:
        log.warning("execution.timeout", session_id=state["session_id"], error=str(exc))
        return {"execution_error": f"timeout: {exc}"}
    except QueryExecutionError as exc:
        log.warning("execution.error", session_id=state["session_id"], error=str(exc))
        return {"execution_error": str(exc)}
    except Exception as exc:
        log.exception("execution.unexpected", session_id=state["session_id"])
        return {"execution_error": str(exc)}

    log.info(
        "execution.success",
        session_id=state["session_id"],
        row_count=result.row_count,
        execution_time_ms=result.execution_time_ms,
        truncated=result.truncated,
    )
    return {
        "execution_rows": result.rows,
        "execution_columns": result.columns,
        "execution_row_count": result.row_count,
        "execution_time_ms": result.execution_time_ms,
        "execution_truncated": result.truncated,
        "execution_error": None,
        "final_sql": sql,
    }
