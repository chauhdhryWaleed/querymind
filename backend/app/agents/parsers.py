"""Shared parsers for LLM responses."""

from __future__ import annotations

import json
import re
from typing import NamedTuple

_FENCE_RE = re.compile(r"^```(?:json|sql)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)
_SELECT_FALLBACK_RE = re.compile(r"(SELECT\s.+?)(?:```|\Z)", re.DOTALL | re.IGNORECASE)


class SqlPayload(NamedTuple):
    sql: str
    explanation: str


def parse_sql_response(content: str) -> SqlPayload:
    """Extract sql and explanation from an LLM response, tolerating markdown fences and stray prose."""
    stripped = (content or "").strip()
    if not stripped:
        return SqlPayload(sql="", explanation="")

    candidate = _FENCE_RE.sub("", stripped).strip()

    try:
        data = json.loads(candidate)
        return SqlPayload(
            sql=str(data.get("sql", "")).strip(),
            explanation=str(data.get("explanation", "")).strip(),
        )
    except json.JSONDecodeError:
        pass

    match = _SELECT_FALLBACK_RE.search(stripped)
    if match:
        return SqlPayload(sql=match.group(1).strip().rstrip(";"), explanation="")

    return SqlPayload(sql=stripped, explanation="")
