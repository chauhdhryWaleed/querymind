from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
    session_id: str | None = None
    reason: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    id: str
    request_id: str
    rating: str
