from datetime import datetime, timedelta

JOIN_OPENS_BEFORE_MINUTES: int = 15
JOIN_CLOSES_AFTER_MINUTES: int = 180

SCHEDULED: str = "scheduled"
COMPLETED: str = "completed"
NO_SHOW: str = "no_show"
CANCELLED: str = "cancelled"
TERMINAL_STATUSES: frozenset[str] = frozenset({COMPLETED, NO_SHOW, CANCELLED})


def is_join_open(starts_at: datetime, ends_at: datetime, now: datetime) -> bool:
    """Whether a session's join link is currently usable.

    Args:
        starts_at: The session's scheduled start.
        ends_at: The session's scheduled end.
        now: The current time, injected for testability.

    Returns:
        True from `JOIN_OPENS_BEFORE_MINUTES` before `starts_at` until
        `JOIN_CLOSES_AFTER_MINUTES` after `ends_at`.
    """
    window_start = starts_at - timedelta(minutes=JOIN_OPENS_BEFORE_MINUTES)
    window_end = ends_at + timedelta(minutes=JOIN_CLOSES_AFTER_MINUTES)
    return window_start <= now <= window_end


def can_transition(current: str, target: str) -> bool:
    """Whether a session may move from `current` status to `target`.

    Args:
        current: The session's current status.
        target: The status being requested.

    Returns:
        False once `current` is terminal — a session never leaves
        `completed`, `no_show`, or `cancelled`. True otherwise.
    """
    return current not in TERMINAL_STATUSES


def is_session_writable(status: str, starts_at: datetime, ends_at: datetime, now: datetime) -> bool:
    """Whether a session currently accepts chat messages and whiteboard writes.

    Args:
        status: The session's current status.
        starts_at: The session's scheduled start.
        ends_at: The session's scheduled end.
        now: The current time, injected for testability.

    Returns:
        True only while the session is still `scheduled` and its join
        window is open — a session that has ended or was never entered
        should not accept new writes.
    """
    return status == SCHEDULED and is_join_open(starts_at, ends_at, now)
