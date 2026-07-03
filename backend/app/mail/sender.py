"""Email sender backends + magic-link helper.

- LogSender: writes the message to the structured log (dev / until SMTP set).
- SmtpSender: sends via SMTP (blocking smtplib run in a thread). Works with any
  provider (Yandex, Mailgun, Resend SMTP, SES SMTP, ...); credentials come from
  /etc/astrolab/env, never from git.

Templates are loaded from seed/email_templates.json so no user-facing copy is
hardcoded in source.
"""

from __future__ import annotations

import asyncio
import json
import smtplib
from email.message import EmailMessage
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import structlog

from app.config import settings

_log = structlog.get_logger("astrolab.mail")

_TEMPLATES_PATH = Path(__file__).resolve().parents[2] / "seed" / "email_templates.json"


@lru_cache(maxsize=1)
def _templates() -> dict:
    return json.loads(_TEMPLATES_PATH.read_text("utf-8"))


def render(name: str, locale: str, **kw: object) -> tuple[str, str]:
    """Return (subject, text) for a template, falling back to ru then en."""
    tpl = _templates().get(name, {})
    block = tpl.get(locale) or tpl.get("ru") or tpl.get("en") or {}
    subject = str(block.get("subject", "")).format(**kw)
    text = str(block.get("text", "")).format(**kw)
    return subject, text


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, text: str) -> None: ...


class LogSender:
    async def send(self, to: str, subject: str, text: str) -> None:
        # Dev backend: never actually emails. The link is in the body — visible
        # in the service log so the flow is testable without a provider.
        _log.info("mail.log", to=to, subject=subject, body=text)


class SmtpSender:
    def _send_blocking(self, to: str, subject: str, text: str) -> None:
        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(text)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
            if settings.smtp_starttls:
                s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)

    async def send(self, to: str, subject: str, text: str) -> None:
        await asyncio.to_thread(self._send_blocking, to, subject, text)


def get_email_sender() -> EmailSender:
    if settings.email_backend == "smtp" and settings.smtp_host:
        return SmtpSender()
    return LogSender()


async def send_magic_link(to: str, link: str, locale: str = "ru") -> None:
    subject, text = render(
        "magic_link", locale, link=link, ttl=settings.magic_link_ttl_min
    )
    await get_email_sender().send(to, subject, text)
