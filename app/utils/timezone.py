from datetime import datetime
from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo("Asia/Kolkata")


def now_local() -> datetime:
    """Return the current application time in India, as an aware datetime."""
    return datetime.now(APP_TIMEZONE)


def today_local():
    """Return today's date in the application timezone."""
    return now_local().date()
