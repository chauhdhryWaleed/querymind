import json
from datetime import UTC, datetime

import structlog
from redis.asyncio import Redis

from app.schemas.history import ConversationTurn

log = structlog.get_logger(__name__)

_KEY_TEMPLATE = "session:{session_id}:history"


class ConversationMemory:
    """Redis-backed multi-turn conversation history with a TTL refreshed on every write."""

    def __init__(self, redis: Redis, ttl_seconds: int = 86400) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return _KEY_TEMPLATE.format(session_id=session_id)

    async def get_history(self, session_id: str) -> list[ConversationTurn]:
        raw = await self._redis.get(self._key(session_id))
        if not raw:
            return []
        try:
            data = json.loads(raw)
            return [ConversationTurn.model_validate(item) for item in data]
        except Exception:
            log.warning("memory.deserialize_error", session_id=session_id)
            return []

    async def append_turn(self, session_id: str, turn: ConversationTurn) -> None:
        history = await self.get_history(session_id)
        history.append(turn)
        serialized = json.dumps([t.model_dump(mode="json") for t in history])
        await self._redis.setex(self._key(session_id), self._ttl, serialized)

    async def clear(self, session_id: str) -> None:
        await self._redis.delete(self._key(session_id))


def make_result_summary(row_count: int, truncated: bool) -> str:
    suffix = " (truncated)" if truncated else ""
    return f"Returned {row_count} row{'s' if row_count != 1 else ''}{suffix}"


def make_conversation_turn(
    question: str,
    sql: str,
    row_count: int,
    truncated: bool,
) -> ConversationTurn:
    return ConversationTurn(
        question=question,
        sql=sql,
        result_summary=make_result_summary(row_count, truncated),
        timestamp=datetime.now(tz=UTC),
    )
