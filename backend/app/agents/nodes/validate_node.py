"""Stage 3: run the validation pipeline against the generated SQL."""

from __future__ import annotations

import structlog

from app.agents.dependencies import AgentDeps
from app.agents.state import AgentState

log = structlog.get_logger(__name__)


async def validate_node(state: AgentState, deps: AgentDeps) -> dict:
    sql = state.get("generated_sql", "")
    result = await deps.validation_pipeline.run(sql, state["raw_schema"], deps.ro_session)

    log.info(
        "validation.result",
        session_id=state["session_id"],
        passed=result.passed,
        stage=result.stage,
        errors=result.errors,
    )

    return {
        "validation_passed": result.passed,
        "validation_errors": result.errors,
        "validation_stage": result.stage,
    }
