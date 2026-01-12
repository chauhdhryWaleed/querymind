import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.schemas.history import ConversationTurn

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)

# Correction strategy lookup: matched against the error string (case-insensitive).
_CORRECTION_STRATEGIES: list[tuple[str, str]] = [
    (
        r"undefined.*table|relation.*does not exist",
        "The table you referenced does not exist. Use only the tables in the schema.",
    ),
    (
        r"undefined.*column|column.*does not exist",
        "The column you referenced does not exist. Use the exact column names from the schema.",
    ),
    (
        r"syntax error",
        "Fix the SQL syntax error. Do not change the query logic, only the syntax.",
    ),
    (
        r"ambiguous column",
        "Qualify all column references with their table alias (e.g., t.column_name).",
    ),
    (
        r"division by zero",
        "Wrap the divisor in NULLIF(expr, 0) to prevent division by zero.",
    ),
    (
        r"timeout|canceling statement",
        "Simplify the query to avoid large scans. Add a LIMIT clause. "
        "Break complex logic into a CTE.",
    ),
    (
        r"operator does not exist|cannot cast",
        "Fix the type mismatch. Cast values explicitly using ::type syntax "
        "(e.g., value::text, value::numeric).",
    ),
]


def _classify_error(error_message: str) -> str:
    lower = error_message.lower()
    for pattern, strategy in _CORRECTION_STRATEGIES:
        if re.search(pattern, lower):
            return strategy
    return (
        "Carefully review the error message and fix the query. "
        "Ensure all referenced tables and columns exist in the schema."
    )


def build_system_prompt(
    schema_context: str,
    conversation_history: list[ConversationTurn] | None = None,
    few_shot_examples: list[dict] | None = None,
) -> str:
    template = _env.get_template("system.j2")
    return template.render(
        schema_context=schema_context,
        conversation_history=conversation_history or [],
        few_shot_examples=few_shot_examples or [],
    )


def build_interpret_prompt(
    question: str,
    sql: str,
    rows: list[dict],
    columns: list[str],
    row_count: int,
    truncated: bool,
) -> str:
    template = _env.get_template("interpret.j2")
    return template.render(
        question=question,
        sql=sql,
        rows=rows,
        columns=columns,
        row_count=row_count,
        truncated=truncated,
    )


def build_correction_prompt(
    question: str,
    failed_sql: str,
    error_message: str,
    schema_context: str,
    correction_history: list[dict] | None = None,
) -> str:
    strategy = _classify_error(error_message)
    template = _env.get_template("correction.j2")
    return template.render(
        question=question,
        failed_sql=failed_sql,
        error_message=error_message,
        correction_strategy=strategy,
        schema_context=schema_context,
        correction_history=correction_history or [],
    )
