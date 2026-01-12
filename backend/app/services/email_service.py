"""Builds transactional emails and dispatches via arq, falling back to inline when no pool."""

from __future__ import annotations

from typing import Any

from app.config.settings import Settings
from app.jobs.email import send_email


class EmailService:
    def __init__(self, settings: Settings, arq_pool: Any | None = None) -> None:
        self._settings = settings
        self._pool = arq_pool

    async def _dispatch(self, *, to: str, subject: str, html: str) -> None:
        if self._pool is not None:
            await self._pool.enqueue_job("send_email", to=to, subject=subject, html=html)
        else:
            await send_email({}, to=to, subject=subject, html=html)

    async def send_password_reset(self, to: str, token: str) -> None:
        link = f"{self._settings.FRONTEND_URL}/reset-password?token={token}"
        html = (
            "<p>You requested a password reset.</p>"
            f'<p><a href="{link}">Reset your password</a></p>'
            "<p>This link expires in 1 hour. If you did not request it, ignore this email.</p>"
            "<p><strong>Note:</strong> resetting your password makes previously saved "
            "database credentials unrecoverable: you will need to re-enter them.</p>"
        )
        await self._dispatch(to=to, subject="Reset your QueryMind password", html=html)

    async def send_verification(self, to: str, token: str) -> None:
        link = f"{self._settings.FRONTEND_URL}/verify-email?token={token}"
        html = (
            "<p>Welcome to QueryMind! Confirm your email to enable password recovery.</p>"
            f'<p><a href="{link}">Verify your email</a></p>'
        )
        await self._dispatch(to=to, subject="Verify your QueryMind email", html=html)
