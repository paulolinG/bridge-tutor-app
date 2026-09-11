from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase, run_query

TABLE = "sessions"


async def list_tutor_sessions(tutor_id: UUID) -> list[dict[str, Any]]:
    """Fetches every session a tutor has held, with what impact needs.

    The diagnostic scores and the microtopic come back as nested embeds in a
    single round trip, the same shape `db/matching.py` uses for pending
    requests.

    Args:
        tutor_id: The tutor whose impact record is being built.

    Returns:
        Session rows carrying their request, student, microtopic and both
        diagnostic form scores.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .select(
            "id, status, session_requests(student_id, duration_minutes, microtopics(label)),"
            " session_diagnostic_forms(kind, score_percent)"
        )
        .eq("tutor_id", str(tutor_id))
        .execute()
    )
    return result.data or []
