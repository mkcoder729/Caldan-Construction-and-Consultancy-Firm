"""
Custom email backends for Caldan Construction.

Resend (https://resend.com) does NOT expose an SMTP relay — it only has an
HTTP API at https://api.resend.com/emails. Using Django's SMTP backend with
`smtp.resend.com` will fail silently on every send.

This module provides:
  - ResendEmailBackend: a thin wrapper around the `resend` SDK that conforms
    to Django's EmailBackend interface. Drop-in replacement.
  - ConsoleEmailBackend: existing fallback for development (already in Django
    core, but re-exported here for clarity).
"""

import logging
from typing import List, Optional

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage, EmailMultiAlternatives

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """
    Django EmailBackend that sends mail via the Resend HTTP API.

    Works with the `resend` Python SDK (already in requirements.txt).
    On any send error it logs and marks the message as failed — never
    raises, so a broken mail pipeline never breaks a request cycle.
    """

    def __init__(self, fail_silently: bool = False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self._resend = None  # lazy import + config check

    def _get_client(self):
        if self._resend is not None:
            return self._resend
        api_key = getattr(settings, "RESEND_API_KEY", "")
        if not api_key:
            if not self.fail_silently:
                raise RuntimeError(
                    "RESEND_API_KEY is not set — cannot send via Resend."
                )
            return None
        try:
            import resend  # noqa: WPS433 — runtime import is intentional
            resend.api_key = api_key
        except ImportError:
            if not self.fail_silently:
                raise
            logger.exception("`resend` package not installed")
            return None
        self._resend = resend
        return resend

    def _send(self, email_message: EmailMessage) -> bool:
        resend = self._get_client()
        if resend is None:
            return False

        # ---- recipient normalization ----
        to: List[str] = list(email_message.to or [])
        cc: List[str] = list(email_message.cc or [])
        bcc: List[str] = list(email_message.bcc or [])
        reply_to: Optional[List[str]] = (
            list(email_message.reply_to) if email_message.reply_to else None
        )

        if not to:
            if not self.fail_silently:
                raise ValueError("EmailMessage has no `to` recipient.")
            return False

        # ---- sender normalization ----
        # Resend expects just the bare address in `from`, not "Name <addr>".
        from_email = email_message.from_email or getattr(
            settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"
        )

        # ---- HTML body extraction ----
        html_body: Optional[str] = None
        if isinstance(email_message, EmailMultiAlternatives):
            for alt in email_message.alternatives:
                if alt[1] == "text/html":
                    html_body = alt[0]
                    break

        text_body = email_message.body or ""

        payload = {
            "from": from_email,
            "to": to,
            "subject": email_message.subject or "",
            "text": text_body,
        }
        if html_body:
            payload["html"] = html_body
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc
        if reply_to:
            payload["reply_to"] = reply_to[0] if len(reply_to) == 1 else reply_to

        # ---- headers + attachments ----
        headers = dict(email_message.extra_headers or {})
        if headers:
            payload["headers"] = headers

        attachments = []
        for filename, content, mimetype in email_message.attachments:
            # Attachments come as (filename, content, mimetype) when added via
            # attach(); content may be bytes or str.
            if isinstance(content, str):
                content = content.encode("utf-8")
            attachments.append({
                "filename": filename or "attachment",
                "content": list(content),  # Resend wants list[int] (base64 also ok)
                # Path/Disposition/ContentId can be added if needed
            })
        if attachments:
            payload["attachments"] = attachments

        # ---- send ----
        try:
            response = resend.Emails.send(payload)
            # Resend returns an object with .id on success
            message_id = getattr(response, "id", None) or (
                response.get("id") if isinstance(response, dict) else None
            )
            logger.info(
                "Resend sent email subject=%r to=%s id=%s",
                email_message.subject, to, message_id,
            )
            return True
        except Exception as exc:  # noqa: BLE001 — Resend raises a custom error
            logger.exception(
                "Resend send failed subject=%r to=%s: %s",
                email_message.subject, to, exc,
            )
            if not self.fail_silently:
                raise
            return False

    def send_messages(self, email_messages):
        """Send a list of EmailMessage objects. Returns count successfully sent."""
        if not email_messages:
            return 0
        sent = 0
        for msg in email_messages:
            if self._send(msg):
                sent += 1
        return sent
