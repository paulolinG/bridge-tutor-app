from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase, run_query

TABLE = "session_messages"


async def create_message(session_id: UUID, sender_role: str, content: str) -> dict[str, Any]:
    """Persists one chat message.

    Args:
        session_id: The session this message belongs to.
        sender_role: Who sent it — 'tutor' or 'student'.
        content: The message text.

    Returns:
        The inserted row.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .insert({"session_id": str(session_id), "sender_role": sender_role, "content": content})
        .execute()
    )
    return result.data[0]


async def list_messages(session_id: UUID) -> list[dict[str, Any]]:
    """Fetches a session's chat history, oldest first.

    Args:
        session_id: The session to fetch messages for.

    Returns:
        Message rows ordered by `created_at` ascending.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .select("*")
        .eq("session_id", str(session_id))
        .order("created_at")
        .execute()
    )
    return result.data
