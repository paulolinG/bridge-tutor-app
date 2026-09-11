from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase, run_query

SESSIONS_TABLE = "sessions"
REQUESTS_TABLE = "session_requests"
EXPIRED: str = "expired"


async def list_unnotified_matches() -> list[dict[str, Any]]:
    """Fetches every matched session not yet reported in a Coordinator Digest.

    Returns:
        Raw rows carrying the join token and the nested student/microtopic
        embed, for `MatchedSession.from_row`.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(SESSIONS_TABLE)
        .select(
            "id, join_token, starts_at,"
            " session_requests(microtopics(label),"
            " student_profiles(display_name, phone_number))"
        )
        .is_("coordinator_notified_at", "null")
        .execute()
    )
    return result.data


async def list_unnotified_expirations() -> list[dict[str, Any]]:
    """Fetches every expired request not yet reported in a Coordinator Digest.

    Returns:
        Raw rows carrying the nested student/microtopic embed, for
        `ExpiredRequest.from_row`.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(REQUESTS_TABLE)
        .select("id, starts_at, microtopics(label), student_profiles(display_name, phone_number)")
        .eq("status", EXPIRED)
        .is_("coordinator_notified_at", "null")
        .execute()
    )
    return result.data


async def mark_notified(session_ids: list[UUID], request_ids: list[UUID]) -> None:
    """Stamps every item a successfully sent digest covered.

    Args:
        session_ids: Matched sessions the digest reported.
        request_ids: Expired requests the digest reported.
    """
    now = datetime.now(UTC).isoformat()
    if session_ids:
        await run_query(
            lambda: get_supabase()
            .table(SESSIONS_TABLE)
            .update({"coordinator_notified_at": now})
            .in_("id", [str(session_id) for session_id in session_ids])
            .execute()
        )
    if request_ids:
        await run_query(
            lambda: get_supabase()
            .table(REQUESTS_TABLE)
            .update({"coordinator_notified_at": now})
            .in_("id", [str(request_id) for request_id in request_ids])
            .execute()
        )
