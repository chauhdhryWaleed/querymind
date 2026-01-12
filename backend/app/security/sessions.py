"""Session tokens, cookies, CSRF, and the Redis-backed ENC_KEY store; the cookie holds only an opaque session id."""

from __future__ import annotations

import base64
import hashlib
import secrets

from fastapi import Response
from redis.asyncio import Redis

SESSION_COOKIE = "t2s_session"
REFRESH_COOKIE = "t2s_refresh"
CSRF_HEADER = "X-CSRF-Token"

_TOKEN_BYTES = 32
_ENC_KEY_PREFIX = "enckey:"


def new_token() -> str:
    """A fresh URL-safe opaque token (session id, refresh token, etc.)."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """SHA-256 hex digest. Tokens are high-entropy, so a plain hash (no Argon2)
    is sufficient and keeps lookups cheap."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)


def _enc_key_redis_key(session_id: str) -> str:
    return f"{_ENC_KEY_PREFIX}{session_id}"


async def store_enc_key(redis: Redis, session_id: str, enc_key: bytes, ttl: int) -> None:
    await redis.set(
        _enc_key_redis_key(session_id),
        base64.b64encode(enc_key).decode("ascii"),
        ex=ttl,
    )


async def get_enc_key(redis: Redis, session_id: str) -> bytes | None:
    raw = await redis.get(_enc_key_redis_key(session_id))
    if raw is None:
        return None
    return base64.b64decode(raw)


async def delete_enc_key(redis: Redis, session_id: str) -> None:
    await redis.delete(_enc_key_redis_key(session_id))


def set_session_cookies(
    response: Response,
    *,
    session_id: str,
    refresh_token: str,
    secure: bool,
    samesite: str = "lax",
    session_ttl: int,
    refresh_ttl: int,
) -> None:
    """Issue httpOnly cookies. In production SameSite=None enables cross-domain auth."""
    common = {"httponly": True, "secure": secure, "samesite": samesite, "path": "/"}
    response.set_cookie(SESSION_COOKIE, session_id, max_age=session_ttl, **common)
    response.set_cookie(REFRESH_COOKIE, refresh_token, max_age=refresh_ttl, **common)


def clear_session_cookies(response: Response, *, secure: bool, samesite: str = "lax") -> None:
    common = {"httponly": True, "secure": secure, "samesite": samesite, "path": "/"}
    response.delete_cookie(SESSION_COOKIE, **common)
    response.delete_cookie(REFRESH_COOKIE, **common)
