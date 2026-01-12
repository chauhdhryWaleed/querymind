"""Serialize query results to CSV or JSON for download."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID


def to_csv(columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_stringify(row.get(c)) for c in columns])
    return buffer.getvalue().encode("utf-8")


def to_json(columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    payload = {
        "columns": columns,
        "row_count": len(rows),
        "rows": [{c: _jsonable(row.get(c)) for c in columns} for row in rows],
    }
    return json.dumps(payload, indent=2, default=_jsonable).encode("utf-8")


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
