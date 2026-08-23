from datetime import datetime
from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")


def now_local() -> datetime:
    """Return the current India local time as a naive datetime.

    MySQL DATETIME has no timezone information. Returning the India clock
    time without tzinfo prevents the database driver from treating the value
    as UTC or performing an unintended timezone conversion.
    """
    return datetime.now(APP_TIMEZONE).replace(tzinfo=None)


def today_local():
    """Return today's date in the application timezone."""
    return datetime.now(APP_TIMEZONE).date()
