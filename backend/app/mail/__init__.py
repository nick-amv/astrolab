"""Transactional email (magic-link delivery).

User-facing copy lives in seed/email_templates.json (data, not source) so the
cyrillic-in-source lint stays clean. The sender backend is chosen by config:
`smtp` for real delivery, `log` (default) prints the link — used in dev and
until SMTP credentials are set in /etc/astrolab/env.
"""

from __future__ import annotations

from app.mail.sender import get_email_sender, send_magic_link

__all__ = ["get_email_sender", "send_magic_link"]
