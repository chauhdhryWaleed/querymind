"""Stage 5: error-classified self-correction. Runs until success or retry cap."""

from __future__ import annotations

import structlog

from app.agents.dependencies import AgentDeps
from app.agents.parsers import parse_sql_response
from app.agents.state import AgentState, CorrectionAttempt
from app.llm.base import Message
from app.prompts.builder import build_correction_prompt

log = structlog.get_logger(__name__)


async def correct_node(state: AgentState, deps: AgentDeps) -> dict:
    error_message = _last_error(state)
    failed_sql = state.get("generated_sql", "")
    retry_count = state.get("retry_count", 0) + 1

    log.info(
        "correction.attempt",
        session_id=state["session_id"],
        retry_count=retry_count,
        error=error_message[:200],
    )

    correction_history = list(state.get("correction_history", []))
    correction_history.append(
        CorrectionAttempt(
            attempt=retry_count,
            failed_sql=failed_sql,
            error=error_message,
            strategy="",
        )
    )

    system = build_correction_prompt(
        question=state["question"],
        failed_sql=failed_sql,
        error_message=error_message,
        schema_context=state["schema_context"],
        correction_history=[dict(a) for a in correction_history[:-1]],
    )

    response = await deps.llm.generate(
        system=system,
        messages=[Message(role="user", content="Generate the corrected SQL.")],
    )

    payload = parse_sql_response(response.content)

    return {
        "generated_sql": payload.sql,
        "sql_explanation": payload.explanation,
        "retry_count": retry_count,
        "correction_history": correction_history,
        "validation_passed": False,
        "execution_error": None,
        "input_tokens": state.get("input_tokens", 0) + response.input_tokens,
        "output_tokens": state.get("output_tokens", 0) + response.output_tokens,
    }


def _last_error(state: AgentState) -> str:
    if state.get("execution_error"):
        return state["execution_error"] or ""
    return "; ".join(state.get("validation_errors", ["Unknown error"]))
