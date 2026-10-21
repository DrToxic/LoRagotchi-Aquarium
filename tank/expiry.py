"""Display-copy retention only. Never deletes history or schedules radio work."""
from datetime import datetime, timezone
import math
import time

MAX_HOURS = 8760  # One year; 0 disables expiry.


def validate_hours(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= MAX_HOURS:
        raise ValueError('Fish lifespan must be 0..8760 hours (0 disables expiry)')
    return float(value)


def timestamp(value):
    """Existing SQLite CURRENT_TIMESTAMP values are UTC, not local wall time."""
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.timestamp()
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None  # Undated legacy rows remain visible; never invent a new share.


def display_state(records, hours=0, now=None):
    """Filter (snapshot, persisted UTC seconds) records, without mutating them."""
    hours = validate_hours(hours)
    now = time.time() if now is None else now
    fish, shared, expired, undated = [], {}, 0, 0
    for snapshot, accepted in records:
        if accepted is None:
            undated += 1
        elif hours and now >= accepted + hours * 3600:
            expired += 1
            continue
        fish.append(snapshot)
        shared[snapshot.owner] = accepted
    return dict(fish=fish, lifespan=dict(hours=hours, expired=expired,
                                       undated=undated, last_shared=shared))


def remaining_text(shared_at, hours, now=None):
    if not hours:
        return 'Expiry off'
    if shared_at is None:
        return 'No saved share time; retained'
    seconds = max(0, shared_at + hours * 3600 - (time.time() if now is None else now))
    if seconds < 60:
        return 'Expires in less than a minute'
    minutes = math.ceil(seconds / 60)
    if minutes < 60:
        return f'Expires in {minutes} min'
    if minutes < 1440:
        return f'Expires in {minutes // 60}h {minutes % 60}m'
    return f'Expires in {minutes // 1440}d {(minutes % 1440) // 60}h'
