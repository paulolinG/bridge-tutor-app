from datetime import datetime
from typing import Any

from app.services.sessions import CANCELLED, COMPLETED, SCHEDULED, is_join_open

PERCENT_SCALE: float = 100.0


def score_answers(items: list[dict[str, Any]], answers: list[int]) -> float:
    """Scores a submitted diagnostic form deterministically.

    Args:
        items: The form's items, each carrying a `correct_index`.
        answers: The student's chosen option index per item, positionally
            aligned with `items`.

    Returns:
        The percentage of items answered correctly, 0.0 to 100.0.
    """
    if not items:
        return 0.0
    correct = sum(
        1 for item, answer in zip(items, answers, strict=False) if item["correct_index"] == answer
    )
    return correct / len(items) * PERCENT_SCALE


def delta_growth(
    status: str,
    baseline_percent: float | None,
    exit_percent: float | None,
) -> float | None:
    """The session's Delta Growth: the exit ticket's gain over the baseline.

    Args:
        status: The session's current status.
        baseline_percent: The Baseline Diagnostic's score, or None if it was
            skipped or never submitted.
        exit_percent: The Exit Ticket's score, or None if never submitted.

    Returns:
        The percentage-point difference, or None when the session did not
        complete or either side is missing. Never 0.0 as a stand-in for a
        missing baseline — that would manufacture a fake delta into the
        number tutors put on college applications.
    """
    if status != COMPLETED:
        return None
    if baseline_percent is None or exit_percent is None:
        return None
    return exit_percent - baseline_percent


def is_baseline_open(status: str, starts_at: datetime, ends_at: datetime, now: datetime) -> bool:
    """Whether the Baseline Diagnostic may still be offered and submitted.

    Args:
        status: The session's current status.
        starts_at: The session's scheduled start.
        ends_at: The session's scheduled end.
        now: The current time, injected for testability.

    Returns:
        True while the session is still `scheduled` and its join window is
        open. Reuses the join window so the baseline is reachable exactly as
        early as the session itself.
    """
    return status == SCHEDULED and is_join_open(starts_at, ends_at, now)


def is_exit_ticket_open(status: str, starts_at: datetime, ends_at: datetime, now: datetime) -> bool:
    """Whether the Exit Ticket may be shown and submitted.

    Deliberately not `is_session_writable`: that helper requires the session
    to still be `scheduled`, but the Exit Ticket exists to be answered once
    the tutor has already marked the session `completed`.

    Args:
        status: The session's current status.
        starts_at: The session's scheduled start.
        ends_at: The session's scheduled end.
        now: The current time, injected for testability.

    Returns:
        True while the join window is open, the session was not cancelled,
        and the session has either been completed or run past `ends_at` —
        the time-based half covers a tutor who forgets to end the session.
    """
    if status == CANCELLED or not is_join_open(starts_at, ends_at, now):
        return False
    return status == COMPLETED or now >= ends_at
