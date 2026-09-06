from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.supabase import get_supabase, run_query

TABLE = "tutor_profiles"

UNIQUE_VIOLATION: str = "23505"


async def get_tutor_profile(tutor_id: UUID) -> dict[str, Any] | None:
    result = await run_query(
        lambda: get_supabase().table(TABLE).select("*").eq("id", str(tutor_id)).execute()
    )
    return result.data[0] if result.data else None


async def create_tutor_profile(tutor_id: UUID, email: str, display_name: str) -> dict[str, Any]:
    """Creates a tutor_profiles row, or returns the existing one on a concurrent conflict.

    Two requests for the same brand-new tutor can both pass the caller's existence
    check before either insert commits; the second insert then hits a primary-key
    conflict here rather than surfacing as an unhandled 500.
    """
    try:
        result = await run_query(
            lambda: get_supabase()
            .table(TABLE)
            .insert({"id": str(tutor_id), "email": email, "display_name": display_name})
            .execute()
        )
        return result.data[0]
    except APIError as exc:
        if getattr(exc, "code", None) != UNIQUE_VIOLATION:
            raise
        existing = await get_tutor_profile(tutor_id)
        if existing is None:
            raise
        return existing
