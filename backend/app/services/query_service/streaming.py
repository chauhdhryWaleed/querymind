"""SSE event formatting and per-node payload projection for the streaming API."""

from __future__ import annotations

import json
from typing import Any

STAGE_LABEL = {
    "schema": "Loading schema",
    "generate": "Generating SQL",
    "validate": "Validating SQL",
    "execute": "Executing query",
    "correct": "Self-correcting",
    "interpret": "Interpreting results",
}


def stage_payload(node: str, delta: dict[str, Any]) -> dict[str, Any]:
    """Project a node delta to a small, UI-safe payload that never leaks raw rows."""
    if node == "schema":
        tables = (delta.get("raw_schema") or {}).get("tables", {})
        return {"table_count": len(tables)}
    if node == "generate":
        return {"sql_preview": (delta.get("generated_sql") or "")[:200]}
    if node == "validate":
        return {
            "passed": bool(delta.get("validation_passed")),
            "stage": delta.get("validation_stage"),
            "errors": (delta.get("validation_errors") or [])[:3],
        }
    if node == "execute":
        return {
            "row_count": delta.get("execution_row_count", 0),
            "execution_time_ms": delta.get("execution_time_ms", 0.0),
            "error": delta.get("execution_error"),
        }
    if node == "correct":
        return {"retry_count": delta.get("retry_count", 0)}
    if node == "interpret":
        return {"answer_preview": (delta.get("natural_language_answer") or "")[:200]}
    return {}


def sse_event(event_type: str, data: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"
