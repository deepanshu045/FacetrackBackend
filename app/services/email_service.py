"""Shared Resend email delivery helpers."""

import logging

import resend

from app.config import RESEND_API_KEY, RESEND_SENDER


logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when Resend cannot accept an email for delivery."""


def is_email_configured() -> bool:
    return bool(RESEND_API_KEY and RESEND_SENDER)


def send_email(*, recipient: str, subject: str, text: str) -> None:
    """Submit a plain-text transactional email through Resend."""
    if not is_email_configured():
        raise EmailDeliveryError("Resend email is not configured.")

    resend.api_key = RESEND_API_KEY
    try:
        resend.Emails.send(
            {
                "from": RESEND_SENDER,
                "to": [recipient],
                "subject": subject,
                "text": text,
            }
        )
    except Exception as error:
        logger.exception("Resend rejected the email delivery request.")
        raise EmailDeliveryError("Resend was unable to send the email.") from error
