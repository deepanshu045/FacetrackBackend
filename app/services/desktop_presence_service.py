from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock


_lock = Lock()
_last_seen: dict[int, datetime] = {}


def mark_desktop_seen(college_id: int) -> None:
    with _lock:
        _last_seen[int(college_id)] = datetime.now(timezone.utc)


def desktop_status(college_id: int, timeout_seconds: int = 25) -> dict:
    with _lock:
        seen = _last_seen.get(int(college_id))

    now = datetime.now(timezone.utc)
    online = bool(seen and (now - seen).total_seconds() <= timeout_seconds)
    return {
        "online": online,
        "last_seen_at": seen.isoformat() if seen else None,
        "timeout_seconds": timeout_seconds,
    }
