from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.notification import ExpiredRequest, MatchedSession

TORONTO = ZoneInfo("America/Toronto")


@dataclass(frozen=True, slots=True)
class Digest:
    subject: str
    body: str


def _format_time(starts_at: datetime) -> str:
    return starts_at.astimezone(TORONTO).strftime("%-I:%M %p")


def _match_line(match: MatchedSession, frontend_origin: str) -> str:
    join_url = f"{frontend_origin}/join/{match.join_token}"
    return (
        f"- {match.student_display_name} ({match.student_phone_number}) — "
        f"{match.microtopic_label} at {_format_time(match.starts_at)}: {join_url}"
    )


def _pluralize(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _subject(matches: list[MatchedSession], expirations: list[ExpiredRequest]) -> str:
    parts = []
    if matches:
        parts.append(_pluralize(len(matches), "new match", "new matches"))
    if expirations:
        parts.append(_pluralize(len(expirations), "expired request", "expired requests"))
    return f"Bridge AI: {', '.join(parts)}"


def _expiration_line(expiration: ExpiredRequest) -> str:
    return (
        f"- {expiration.student_display_name} ({expiration.student_phone_number}) — "
        f"{expiration.microtopic_label}, was requested for "
        f"{_format_time(expiration.starts_at)}"
    )


def build_digest(
    matches: list[MatchedSession],
    expirations: list[ExpiredRequest],
    frontend_origin: str,
) -> Digest | None:
    """Builds the Coordinator Digest for one batch run's outstanding work.

    Args:
        matches: Sessions not yet reported to the coordinator.
        expirations: Session requests not yet reported to the coordinator.
        frontend_origin: The frontend's base URL, used to build join links.

    Returns:
        None when there is nothing outstanding — a run with nothing to
        report sends nothing.
    """
    if not matches and not expirations:
        return None

    sections = []
    if matches:
        sections.append(
            "New matches:\n" + "\n".join(_match_line(m, frontend_origin) for m in matches)
        )
    if expirations:
        sections.append("Expired requests:\n" + "\n".join(_expiration_line(e) for e in expirations))

    return Digest(subject=_subject(matches, expirations), body="\n\n".join(sections))
