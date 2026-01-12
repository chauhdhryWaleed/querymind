from __future__ import annotations

from pydantic import BaseModel


class ProviderBreakdown(BaseModel):
    provider: str
    query_count: int
    input_tokens: int
    output_tokens: int


class StatsResponse(BaseModel):
    window_days: int
    query_count: int
    successful_query_count: int
    failed_query_count: int
    total_input_tokens: int
    total_output_tokens: int
    avg_execution_time_ms: float
    avg_retry_count: float
    feedback_up: int
    feedback_down: int
    providers: list[ProviderBreakdown]
