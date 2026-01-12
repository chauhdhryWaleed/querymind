"""Per-request identity and resources resolved by the query endpoint."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.services.retrieval_service import RetrievalResult


@dataclass
class QueryContext:
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    connection_id: uuid.UUID
    llm_key_id: uuid.UUID | None
    llm_provider_name: str
    retrieval: RetrievalResult
