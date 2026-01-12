"""LangGraph topology for the QueryMind agent."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.dependencies import AgentDeps
from app.agents.nodes.correct_node import correct_node
from app.agents.nodes.execute_node import execute_node
from app.agents.nodes.generate_node import generate_node
from app.agents.nodes.interpret_node import interpret_node
from app.agents.nodes.schema_node import schema_node
from app.agents.nodes.validate_node import validate_node
from app.agents.state import AgentState

NodeFn = Callable[[AgentState, AgentDeps], Awaitable[dict]]

_NODES: dict[str, NodeFn] = {
    "schema": schema_node,
    "generate": generate_node,
    "validate": validate_node,
    "execute": execute_node,
    "correct": correct_node,
    "interpret": interpret_node,
}


def _bind(node: NodeFn, deps: AgentDeps) -> Callable[[AgentState], Awaitable[dict]]:
    async def _node(state: AgentState) -> dict:
        return await node(state, deps)

    return _node


def _route_after_validation(state: AgentState) -> str:
    if state.get("validation_passed"):
        return "execute"
    if state.get("retry_count", 0) >= state.get("max_retries", 3):
        return END
    return "correct"


def _route_after_execution(state: AgentState) -> str:
    if state.get("execution_error") is None:
        return "interpret"
    if state.get("retry_count", 0) >= state.get("max_retries", 3):
        return END
    return "correct"


def _route_after_correction(state: AgentState) -> str:
    if state.get("retry_count", 0) >= state.get("max_retries", 3):
        return END
    return "validate"


def build_graph(deps: AgentDeps) -> Any:
    graph = StateGraph(AgentState)

    for name, fn in _NODES.items():
        graph.add_node(name, _bind(fn, deps))

    graph.add_edge(START, "schema")
    graph.add_edge("schema", "generate")
    graph.add_edge("generate", "validate")
    graph.add_edge("interpret", END)

    graph.add_conditional_edges(
        "validate",
        _route_after_validation,
        {"execute": "execute", END: END, "correct": "correct"},
    )
    graph.add_conditional_edges(
        "execute",
        _route_after_execution,
        {"interpret": "interpret", END: END, "correct": "correct"},
    )
    graph.add_conditional_edges(
        "correct",
        _route_after_correction,
        {"validate": "validate", END: END},
    )

    return graph.compile()
