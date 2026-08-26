"""Shared Brevo email delivery helpers."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME


logger = logging.getLogger(__name__)
BREVO_SEND_EMAIL_URL = "https://api.brevo.com/v3/smtp/email"


class EmailDeliveryError(RuntimeError):
    """Raised when Brevo cannot accept an email for delivery."""


def is_email_configured() -> bool:
    return bool(BREVO_API_KEY and BREVO_SENDER_EMAIL)


def send_email(*, recipient: str, subject: str, text: str) -> None:
    """Submit a plain-text transactional email through Brevo."""
    if not is_email_configured():
        raise EmailDeliveryError("Brevo email is not configured.")

    payload = {
        "sender": {"email": BREVO_SENDER_EMAIL, "name": BREVO_SENDER_NAME},
        "to": [{"email": recipient}],
        "subject": subject,
        "textContent": text,
    }
    request = Request(
        BREVO_SEND_EMAIL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            if response.status < 200 or response.status >= 300:
                raise EmailDeliveryError(
                    f"Brevo returned unexpected HTTP status {response.status}."
                )
    except (HTTPError, URLError, TimeoutError, EmailDeliveryError) as error:
        logger.exception("Brevo rejected the email delivery request.")
        raise EmailDeliveryError("Brevo was unable to send the email.") from error
