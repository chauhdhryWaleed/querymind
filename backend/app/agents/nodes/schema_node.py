"""Stage 1: passthrough; the schema slice is pre-seeded into state by the RetrievalService."""

from __future__ import annotations

from app.agents.dependencies import AgentDeps
from app.agents.state import AgentState


async def schema_node(state: AgentState, deps: AgentDeps) -> dict:
    return {}
