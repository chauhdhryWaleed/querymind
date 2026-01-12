from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SaveFavoriteRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    question: str = Field(..., min_length=3, max_length=2000)
    sql: str = Field(..., min_length=3, max_length=10_000)
    tags: str | None = None


class FavoriteItem(BaseModel):
    id: str
    name: str
    question: str
    sql: str
    tags: str | None = None
    created_at: datetime


class FavoritesResponse(BaseModel):
    items: list[FavoriteItem]
    total: int
