"""send_email arq task; logs the email instead of sending when RESEND_API_KEY is unset."""

from __future__ import annotations

import structlog

from app.config.settings import get_settings

log = structlog.get_logger(__name__)


async def send_email(ctx: dict, *, to: str, subject: str, html: str) -> dict:
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        # Dev/test mode: log instead of send so the reset link is recoverable without a provider.
        log.info("email.dev_noop", to=to, subject=subject, html=html)
        return {"sent": False, "mode": "dev-log"}

    import resend

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send(
        {
            "from": settings.EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "html": html,
        }
    )
    log.info("email.sent", to=to, subject=subject)
    return {"sent": True, "mode": "resend"}
