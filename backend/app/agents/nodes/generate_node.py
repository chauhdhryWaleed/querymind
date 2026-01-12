"""Stage 2: ask the LLM to generate SQL from the user's question."""

from __future__ import annotations

import structlog

from app.agents.dependencies import AgentDeps
from app.agents.parsers import parse_sql_response
from app.agents.state import AgentState
from app.llm.base import Message
from app.prompts.builder import build_system_prompt

log = structlog.get_logger(__name__)


async def generate_node(state: AgentState, deps: AgentDeps) -> dict:
    system = build_system_prompt(
        schema_context=state["schema_context"],
        conversation_history=state.get("conversation_history", []),
    )

    response = await deps.llm.generate(
        system=system,
        messages=[Message(role="user", content=state["question"])],
    )

    log.info(
        "llm.generated",
        session_id=state["session_id"],
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
    )

    payload = parse_sql_response(response.content)

    return {
        "generated_sql": payload.sql,
        "sql_explanation": payload.explanation,
        "input_tokens": state.get("input_tokens", 0) + response.input_tokens,
        "output_tokens": state.get("output_tokens", 0) + response.output_tokens,
        # llm_provider is seeded from the BYOK key's provider; do not overwrite it with the global default.
        "validation_passed": False,
        "execution_error": None,
        "agent_error": None,
    }
