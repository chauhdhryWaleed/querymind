"""Recommend a chart type for a result set, server-side to keep the UI dumb and testable."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

ChartType = Literal["table", "bar", "line", "pie", "scatter", "kpi"]


class VisualizationHint(BaseModel):
    model_config = ConfigDict(frozen=True)

    chart: ChartType
    x: str | None = None
    y: list[str] = []
    label: str | None = None
    reason: str = ""


_TIME_TYPES = (datetime, date)
_NUMERIC_TYPES = (int, float)


def recommend(columns: list[str], rows: list[dict[str, Any]]) -> VisualizationHint:
    if not columns or not rows:
        return VisualizationHint(chart="table", reason="No data to plot")

    if len(rows) == 1 and len(columns) == 1:
        return VisualizationHint(
            chart="kpi",
            label=columns[0],
            y=columns,
            reason="Single scalar result",
        )

    column_types = {col: _infer_type(rows, col) for col in columns}
    numeric_cols = [c for c, t in column_types.items() if t == "numeric"]
    temporal_cols = [c for c, t in column_types.items() if t == "temporal"]
    categorical_cols = [c for c, t in column_types.items() if t == "categorical"]

    if temporal_cols and numeric_cols:
        return VisualizationHint(
            chart="line",
            x=temporal_cols[0],
            y=numeric_cols[:3],
            reason="Temporal x-axis with numeric measures",
        )

    if categorical_cols and len(numeric_cols) == 1 and len(rows) <= 8:
        return VisualizationHint(
            chart="pie",
            label=categorical_cols[0],
            y=numeric_cols,
            reason="Few categories with a single numeric share",
        )

    if categorical_cols and numeric_cols:
        return VisualizationHint(
            chart="bar",
            x=categorical_cols[0],
            y=numeric_cols[:3],
            reason="Categorical x-axis with numeric measures",
        )

    if len(numeric_cols) >= 2:
        return VisualizationHint(
            chart="scatter",
            x=numeric_cols[0],
            y=numeric_cols[1:2],
            reason="Two numeric dimensions",
        )

    return VisualizationHint(chart="table", reason="No clear chart fit")


def _infer_type(rows: list[dict[str, Any]], column: str) -> str:
    sample = [r.get(column) for r in rows[:20] if r.get(column) is not None]
    if not sample:
        return "unknown"

    if all(isinstance(v, _TIME_TYPES) for v in sample):
        return "temporal"
    if all(isinstance(v, _NUMERIC_TYPES) and not isinstance(v, bool) for v in sample):
        return "numeric"
    if all(isinstance(v, str) and _looks_like_date(v) for v in sample):
        return "temporal"
    if all(_looks_like_number(v) for v in sample):
        return "numeric"
    return "categorical"


def _looks_like_date(value: str) -> bool:
    if len(value) < 7:
        return False
    head = value[:10]
    return head.count("-") == 2 and head.replace("-", "").isdigit()


def _looks_like_number(value: Any) -> bool:
    if isinstance(value, _NUMERIC_TYPES) and not isinstance(value, bool):
        return True
    if not isinstance(value, str):
        return False
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
