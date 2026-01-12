"""Agent state. Single source of truth shared across every LangGraph node."""

from __future__ import annotations

from typing import TypedDict

from app.schemas.history import ConversationTurn


class CorrectionAttempt(TypedDict):
    attempt: int
    failed_sql: str
    error: str
    strategy: str


class AgentState(TypedDict, total=False):
    question: str
    session_id: str
    request_id: str

    schema_context: str
    raw_schema: dict
    conversation_history: list[ConversationTurn]

    generated_sql: str
    sql_explanation: str

    validation_errors: list[str]
    validation_passed: bool
    validation_stage: str

    execution_rows: list[dict]
    execution_columns: list[str]
    execution_row_count: int
    execution_time_ms: float
    execution_truncated: bool
    execution_error: str | None

    retry_count: int
    max_retries: int
    correction_history: list[CorrectionAttempt]

    input_tokens: int
    output_tokens: int
    llm_provider: str

    final_sql: str
    natural_language_answer: str
    agent_error: str | None
