from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase, run_query
from app.models.matching import AvailabilityWindow, TutorCandidate
from app.services.matching import to_committed_session

REQUESTS_TABLE = "session_requests"
SESSIONS_TABLE = "sessions"
COMPETENCIES_TABLE = "tutor_microtopic_competencies"
AVAILABILITY_TABLE = "tutor_availability"

PENDING: str = "pending"
MATCHED: str = "matched"
EXPIRED: str = "expired"
SCHEDULED: str = "scheduled"


async def expire_stale_requests(now: datetime) -> int:
    """Flips every pending request whose window has already passed to 'expired'.

    Args:
        now: The current time, used as the expiry cutoff.

    Returns:
        The number of requests expired.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(REQUESTS_TABLE)
        .update({"status": EXPIRED})
        .eq("status", PENDING)
        .lt("starts_at", now.isoformat())
        .execute()
    )
    return len(result.data)


async def list_pending_requests() -> list[dict[str, Any]]:
    """Fetches all pending session requests with their urgency inputs.

    Returns:
        Raw rows including the nested student's academic average and region
        funding-deficit multiplier, for `PendingRequest.from_row`.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(REQUESTS_TABLE)
        .select(
            "id, student_id, microtopic_id, starts_at, duration_minutes, created_at,"
            " student_profiles(academic_average, regions(funding_deficit_multiplier))"
        )
        .eq("status", PENDING)
        .execute()
    )
    return result.data


async def list_certified_tutor_profiles(microtopic_id: UUID) -> list[dict[str, Any]]:
    """Fetches tutors certified in a microtopic who have completed onboarding.

    Args:
        microtopic_id: The microtopic to filter certification on.

    Returns:
        Raw rows with each tutor's id and capacity caps. Tutors who haven't
        set their caps yet (still null, onboarding incomplete) are excluded.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(COMPETENCIES_TABLE)
        .select("tutor_id, tutor_profiles!inner(id, daily_cap_minutes, weekly_cap_minutes)")
        .eq("microtopic_id", str(microtopic_id))
        .execute()
    )
    return [
        row
        for row in result.data
        if row["tutor_profiles"]["daily_cap_minutes"] is not None
        and row["tutor_profiles"]["weekly_cap_minutes"] is not None
    ]


async def list_availability(tutor_ids: list[UUID]) -> list[dict[str, Any]]:
    """Fetches recurring availability windows for a set of tutors.

    Args:
        tutor_ids: The tutors to fetch availability for.

    Returns:
        Raw availability rows, empty if `tutor_ids` is empty.
    """
    if not tutor_ids:
        return []
    result = await run_query(
        lambda: get_supabase()
        .table(AVAILABILITY_TABLE)
        .select("tutor_id, day_of_week, start_minute, end_minute")
        .in_("tutor_id", [str(tutor_id) for tutor_id in tutor_ids])
        .execute()
    )
    return result.data


async def list_scheduled_sessions(
    tutor_ids: list[UUID], range_start: datetime, range_end: datetime
) -> list[dict[str, Any]]:
    """Fetches scheduled sessions for a set of tutors within a time range.

    Args:
        tutor_ids: The tutors to fetch sessions for.
        range_start: Inclusive lower bound on `starts_at`.
        range_end: Exclusive upper bound on `starts_at`.

    Returns:
        Raw session rows, empty if `tutor_ids` is empty.
    """
    if not tutor_ids:
        return []
    result = await run_query(
        lambda: get_supabase()
        .table(SESSIONS_TABLE)
        .select("tutor_id, starts_at, ends_at")
        .in_("tutor_id", [str(tutor_id) for tutor_id in tutor_ids])
        .eq("status", SCHEDULED)
        .gte("starts_at", range_start.isoformat())
        .lt("starts_at", range_end.isoformat())
        .execute()
    )
    return result.data


async def list_candidates(
    microtopic_id: UUID, range_start: datetime, range_end: datetime
) -> list[TutorCandidate]:
    """Assembles the full candidate pool for a microtopic and capacity-accounting range.

    Args:
        microtopic_id: The request's microtopic.
        range_start: Inclusive lower bound for existing-session lookup (the
            start of the request's local week).
        range_end: Exclusive upper bound for existing-session lookup (the end
            of the request's local week).

    Returns:
        One `TutorCandidate` per certified, onboarded tutor, with their
        availability and existing commitments attached.
    """
    profile_rows = await list_certified_tutor_profiles(microtopic_id)
    tutor_ids = [UUID(row["tutor_id"]) for row in profile_rows]

    availability_rows = await list_availability(tutor_ids)
    session_rows = await list_scheduled_sessions(tutor_ids, range_start, range_end)

    availability_by_tutor: dict[UUID, list[AvailabilityWindow]] = {
        tutor_id: [] for tutor_id in tutor_ids
    }
    for row in availability_rows:
        availability_by_tutor[UUID(row["tutor_id"])].append(
            AvailabilityWindow(
                day_of_week=row["day_of_week"],
                start_minute=row["start_minute"],
                end_minute=row["end_minute"],
            )
        )

    commitments_by_tutor: dict[UUID, list] = {tutor_id: [] for tutor_id in tutor_ids}
    for row in session_rows:
        commitments_by_tutor[UUID(row["tutor_id"])].append(
            to_committed_session(
                datetime.fromisoformat(row["starts_at"]), datetime.fromisoformat(row["ends_at"])
            )
        )

    return [
        TutorCandidate(
            tutor_id=UUID(row["tutor_id"]),
            daily_cap_minutes=row["tutor_profiles"]["daily_cap_minutes"],
            weekly_cap_minutes=row["tutor_profiles"]["weekly_cap_minutes"],
            availability=tuple(availability_by_tutor[UUID(row["tutor_id"])]),
            commitments=tuple(commitments_by_tutor[UUID(row["tutor_id"])]),
        )
        for row in profile_rows
    ]


async def claim_request(request_id: UUID) -> bool:
    """Atomically flips a pending request to 'matched'.

    Args:
        request_id: The request to claim.

    Returns:
        True if this call won the claim (the row was still pending), False if
        another concurrent run already claimed or expired it.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(REQUESTS_TABLE)
        .update({"status": MATCHED})
        .eq("id", str(request_id))
        .eq("status", PENDING)
        .execute()
    )
    return len(result.data) > 0


async def create_session(
    request_id: UUID, tutor_id: UUID, starts_at: datetime, ends_at: datetime
) -> dict[str, Any]:
    """Creates the scheduled session for a claimed match.

    Args:
        request_id: The matched session request.
        tutor_id: The chosen tutor.
        starts_at: The session's start time.
        ends_at: The session's end time.

    Returns:
        The inserted session row, including its generated `join_token`.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(SESSIONS_TABLE)
        .insert(
            {
                "request_id": str(request_id),
                "tutor_id": str(tutor_id),
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
            }
        )
        .execute()
    )
    return result.data[0]


async def list_upcoming_sessions(tutor_id: UUID, now: datetime) -> list[dict[str, Any]]:
    """Fetches a tutor's upcoming scheduled sessions with their microtopic label.

    Args:
        tutor_id: The tutor to fetch sessions for.
        now: The current time; only sessions starting after this are returned.

    Returns:
        Raw session rows including the nested microtopic label, ordered soonest first.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(SESSIONS_TABLE)
        .select("id, starts_at, ends_at, join_token, session_requests(microtopics(label))")
        .eq("tutor_id", str(tutor_id))
        .eq("status", SCHEDULED)
        .gte("starts_at", now.isoformat())
        .order("starts_at")
        .execute()
    )
    return result.data
