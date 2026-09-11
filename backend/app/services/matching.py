import random
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.matching import (
    NEUTRAL_ACADEMIC_AVERAGE,
    NEUTRAL_MULTIPLIER,
    TORONTO,
    CommittedSession,
    PendingRequest,
    RequestWindow,
    TutorCandidate,
)


def urgency_score(request: PendingRequest) -> float:
    """Ranks a pending session request for batch-run processing order.

    Args:
        request: The pending request to score.

    Returns:
        The student's academic average multiplied by their region's funding
        deficit multiplier, using neutral defaults when either is unset.
    """
    academic_average = request.academic_average
    if academic_average is None:
        academic_average = NEUTRAL_ACADEMIC_AVERAGE
    multiplier = request.funding_deficit_multiplier
    if multiplier is None:
        multiplier = NEUTRAL_MULTIPLIER
    return academic_average * multiplier


def order_requests(requests: Sequence[PendingRequest]) -> list[PendingRequest]:
    """Orders pending requests for batch-run processing.

    Args:
        requests: The pending requests to order.

    Returns:
        Requests sorted by urgency score descending, with ties broken by
        earliest `created_at` first.
    """
    return sorted(requests, key=lambda request: (-urgency_score(request), request.created_at))


def to_request_window(starts_at: datetime, duration_minutes: int) -> RequestWindow:
    """Converts a request's absolute UTC start time into local minute-of-day terms.

    Args:
        starts_at: The request's absolute start time (must be timezone-aware).
        duration_minutes: The session's fixed length in minutes.

    Returns:
        A `RequestWindow` carrying the local day-of-week and minute range that
        an availability window is compared against. `is_schedulable` is False
        when the local wall-clock span crosses midnight or collapses to zero
        length (a fall-back-hour artifact), since availability windows can
        never represent either case.
    """
    starts_at_utc = starts_at.astimezone(UTC)
    ends_at_utc = starts_at_utc + timedelta(minutes=duration_minutes)

    local_start = starts_at_utc.astimezone(TORONTO)
    local_end = ends_at_utc.astimezone(TORONTO)

    start_minute = local_start.hour * 60 + local_start.minute
    end_minute = local_end.hour * 60 + local_end.minute
    local_date = local_start.date()

    return RequestWindow(
        day_of_week=local_start.weekday(),
        start_minute=start_minute,
        end_minute=end_minute,
        local_date=local_date,
        week_start=local_date - timedelta(days=local_date.weekday()),
        starts_at=starts_at_utc,
        ends_at=ends_at_utc,
        duration_minutes=duration_minutes,
        is_schedulable=(local_end.date() == local_date and end_minute > start_minute),
    )


def covers_window(candidate: TutorCandidate, window: RequestWindow) -> bool:
    """Checks whether a tutor has a recurring availability window containing the request.

    Args:
        candidate: The tutor to check.
        window: The request's converted local time window.

    Returns:
        True if any of the tutor's availability windows fully contains `window`.
    """
    return any(
        availability.day_of_week == window.day_of_week
        and availability.start_minute <= window.start_minute
        and availability.end_minute >= window.end_minute
        for availability in candidate.availability
    )


def has_conflict(candidate: TutorCandidate, window: RequestWindow) -> bool:
    """Checks whether a tutor already has a session overlapping the request window.

    Args:
        candidate: The tutor to check.
        window: The request's time window.

    Returns:
        True if any existing commitment overlaps `window`. Sessions that merely
        abut (one ends exactly when the other starts) do not count as a conflict.
    """
    return any(
        commitment.starts_at < window.ends_at and commitment.ends_at > window.starts_at
        for commitment in candidate.commitments
    )


def within_caps(candidate: TutorCandidate, window: RequestWindow) -> bool:
    """Checks whether adding this request would exceed the tutor's daily or weekly cap.

    Args:
        candidate: The tutor to check, including their already-committed sessions.
        window: The request's time window.

    Returns:
        True if the tutor's committed minutes plus this request's duration stay
        within both `daily_cap_minutes` and `weekly_cap_minutes`.
    """
    daily_committed = sum(
        commitment.duration_minutes
        for commitment in candidate.commitments
        if commitment.local_date == window.local_date
    )
    weekly_committed = sum(
        commitment.duration_minutes
        for commitment in candidate.commitments
        if commitment.week_start == window.week_start
    )
    return (
        daily_committed + window.duration_minutes <= candidate.daily_cap_minutes
        and weekly_committed + window.duration_minutes <= candidate.weekly_cap_minutes
    )


def build_domain(
    candidates: Iterable[TutorCandidate], window: RequestWindow
) -> list[TutorCandidate]:
    """Filters candidate tutors down to those eligible for a request window.

    Args:
        candidates: Tutors already certified in the request's microtopic
            (certification is filtered upstream in the DB layer).
        window: The request's time window.

    Returns:
        Candidates that have availability covering the window, no conflicting
        session, and remaining daily and weekly capacity.
    """
    return [
        candidate
        for candidate in candidates
        if covers_window(candidate, window)
        and not has_conflict(candidate, window)
        and within_caps(candidate, window)
    ]


def select_match(
    candidates: Iterable[TutorCandidate], window: RequestWindow, rng: random.Random
) -> UUID | None:
    """Randomly selects one tutor from the eligible domain for a request.

    Args:
        candidates: Tutors certified in the request's microtopic.
        window: The request's time window.
        rng: The random source to draw from — pass a seeded instance for
            deterministic tests, an unseeded one in production.

    Returns:
        The chosen tutor's id, or None if the domain is empty. The domain is
        sorted by tutor id before selection so the result depends only on the
        rng seed, not on the candidates' input order.
    """
    domain = sorted(build_domain(candidates, window), key=lambda candidate: str(candidate.tutor_id))
    if not domain:
        return None
    return rng.choice(domain).tutor_id


def to_committed_session(starts_at: datetime, ends_at: datetime) -> CommittedSession:
    """Derives the capacity-accounting fields for an existing or newly matched session.

    Args:
        starts_at: The session's absolute start time (timezone-aware).
        ends_at: The session's absolute end time (timezone-aware).

    Returns:
        A `CommittedSession` with `local_date` and `week_start` computed in
        America/Toronto, for use in `within_caps` and `has_conflict`.
    """
    starts_at_utc = starts_at.astimezone(UTC)
    local_date = starts_at_utc.astimezone(TORONTO).date()
    return CommittedSession(
        starts_at=starts_at_utc,
        ends_at=ends_at.astimezone(UTC),
        local_date=local_date,
        week_start=local_date - timedelta(days=local_date.weekday()),
        duration_minutes=int((ends_at - starts_at).total_seconds() // 60),
    )
