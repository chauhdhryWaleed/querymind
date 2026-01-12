"""Shared slowapi rate limiter (keyed by client IP), applied to /auth/* endpoints."""

from __future__ import annotations

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
rate_limit_handler = _rate_limit_exceeded_handler
