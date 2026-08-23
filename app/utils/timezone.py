from datetime import datetime
from zoneinfo import ZoneInfo


# FaceTrack attendance and lecture schedules use India local time.
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")


def now_local() -> datetime:
    """Return the current application time in India (IST)."""
    return datetime.now(APP_TIMEZONE)
