from datetime import datetime

from pydantic import BaseModel


class ConversationTurn(BaseModel):
    question: str
    sql: str
    result_summary: str
    timestamp: datetime


class HistoryItem(BaseModel):
    id: str
    session_id: str
    request_id: str
    question: str
    final_sql: str
    answer: str | None = None
    row_count: int
    retry_count: int
    execution_time_ms: float
    created_at: datetime


class HistoryResponse(BaseModel):
    session_id: str | None = None
    turns: list[HistoryItem]
    total: int
