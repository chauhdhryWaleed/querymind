"""Public request/response schemas for the /query family of endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.services.visualization_service import VisualizationHint


class QueryRequest(BaseModel):
    connection_id: uuid.UUID
    question: str = Field(..., min_length=3, max_length=2000)
    llm_key_id: uuid.UUID | None = None  # falls back to the workspace default key
    session_id: str | None = None


class RetrievedTableHint(BaseModel):
    name: str
    score: float
    via: str
    lexical: float
    vector: float


class RetrievalDisclosure(BaseModel):
    tables: list[RetrievedTableHint]
    schema_tokens: int


class CorrectionStep(BaseModel):
    attempt: int
    failed_sql: str
    error: str


class ResultMetadata(BaseModel):
    retry_count: int
    input_tokens: int
    output_tokens: int
    llm_provider: str
    truncated: bool
    request_id: str
    failed_stage: str | None = None
    corrections: list[CorrectionStep] = []
    retrieval: RetrievalDisclosure | None = None


class QueryResponse(BaseModel):
    answer: str
    sql: str
    explanation: str
    results: list[dict[str, Any]]
    columns: list[str]
    row_count: int
    execution_time_ms: float
    visualization: VisualizationHint
    metadata: ResultMetadata
