"""Stage 6: turn raw SQL results into a plain-English answer."""

from __future__ import annotations

import structlog

from app.agents.dependencies import AgentDeps
from app.agents.state import AgentState
from app.llm.base import Message
from app.prompts.builder import build_interpret_prompt

log = structlog.get_logger(__name__)


async def interpret_node(state: AgentState, deps: AgentDeps) -> dict:
    system = build_interpret_prompt(
        question=state["question"],
        sql=state.get("final_sql") or state.get("generated_sql", ""),
        rows=state.get("execution_rows", []),
        columns=state.get("execution_columns", []),
        row_count=state.get("execution_row_count", 0),
        truncated=state.get("execution_truncated", False),
    )

    response = await deps.llm.generate(
        system=system,
        messages=[Message(role="user", content="Provide the natural language answer.")],
        temperature=0.3,
        json_mode=False,  # interpret returns plain prose, not JSON
    )

    log.info(
        "interpret.generated",
        session_id=state["session_id"],
        tokens=response.output_tokens,
    )

    return {
        "natural_language_answer": response.content.strip(),
        "input_tokens": state.get("input_tokens", 0) + response.input_tokens,
        "output_tokens": state.get("output_tokens", 0) + response.output_tokens,
    }
