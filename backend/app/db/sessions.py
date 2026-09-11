from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase, run_query

TABLE = "sessions"
SCHEDULED: str = "scheduled"
WhiteboardSnapshot = dict[str, Any]


async def get_by_join_token(join_token: str) -> dict[str, Any] | None:
    """Fetches a session by its unguessable join token.

    Args:
        join_token: The token from the join link.

    Returns:
        The session row with its microtopic label, or None if unknown.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .select(
            "id, tutor_id, starts_at, ends_at, status, daily_room_name, whiteboard_snapshot,"
            " session_requests(microtopics(label))"
        )
        .eq("join_token", join_token)
        .execute()
    )
    return result.data[0] if result.data else None


async def set_daily_room_name(session_id: UUID, room_name: str) -> None:
    """Records the Daily room created for a session on its first join.

    Args:
        session_id: The session the room belongs to.
        room_name: The Daily room's name.
    """
    await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .update({"daily_room_name": room_name})
        .eq("id", str(session_id))
        .execute()
    )


async def set_status(
    session_id: UUID, tutor_id: UUID, status: str, completed_at: datetime | None
) -> bool:
    """Atomically transitions a session out of 'scheduled'.

    Args:
        session_id: The session to update.
        tutor_id: The owning tutor — enforced in the query.
        status: The terminal status to set.
        completed_at: When the transition happened, or None.

    Returns:
        True if this call won the transition (the row was still
        'scheduled'), False if it was already terminal.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .update(
            {
                "status": status,
                "completed_at": completed_at.isoformat() if completed_at else None,
            }
        )
        .eq("id", str(session_id))
        .eq("tutor_id", str(tutor_id))
        .eq("status", SCHEDULED)
        .execute()
    )
    return len(result.data) > 0


async def get_for_tutor(session_id: UUID, tutor_id: UUID) -> dict[str, Any] | None:
    """Fetches a session owned by a specific tutor.

    Args:
        session_id: The session to fetch.
        tutor_id: The tutor requesting it — enforced in the query, not in
            Python, so another tutor's session is indistinguishable from a
            nonexistent one.

    Returns:
        The session row, or None if it doesn't exist or isn't this tutor's.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .select("id, starts_at, ends_at, status, daily_room_name, whiteboard_snapshot")
        .eq("id", str(session_id))
        .eq("tutor_id", str(tutor_id))
        .execute()
    )
    return result.data[0] if result.data else None


async def set_whiteboard_snapshot(session_id: UUID, snapshot: WhiteboardSnapshot) -> None:
    """Persists the whiteboard's current document, for reconnects and late joins.

    Args:
        session_id: The session the whiteboard belongs to.
        snapshot: The tldraw document snapshot to store.
    """
    await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .update({"whiteboard_snapshot": snapshot})
        .eq("id", str(session_id))
        .execute()
    )
