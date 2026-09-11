from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase, run_query

AVAILABILITY_TABLE = "tutor_availability"
TUTOR_PROFILES_TABLE = "tutor_profiles"


async def get_availability_windows(tutor_id: UUID) -> list[dict[str, Any]]:
    """Fetches a tutor's recurring availability windows.

    Args:
        tutor_id: The tutor to fetch windows for.

    Returns:
        Raw window rows.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(AVAILABILITY_TABLE)
        .select("day_of_week, start_minute, end_minute")
        .eq("tutor_id", str(tutor_id))
        .execute()
    )
    return result.data


async def replace_availability_windows(tutor_id: UUID, windows: list[dict[str, Any]]) -> None:
    """Replaces all of a tutor's availability windows with a new set.

    Args:
        tutor_id: The tutor whose windows are being replaced.
        windows: The new set of `{day_of_week, start_minute, end_minute}` rows.
    """
    await run_query(
        lambda: get_supabase()
        .table(AVAILABILITY_TABLE)
        .delete()
        .eq("tutor_id", str(tutor_id))
        .execute()
    )
    if not windows:
        return
    await run_query(
        lambda: get_supabase()
        .table(AVAILABILITY_TABLE)
        .insert([{**window, "tutor_id": str(tutor_id)} for window in windows])
        .execute()
    )


async def update_capacity(
    tutor_id: UUID, daily_cap_minutes: int, weekly_cap_minutes: int
) -> dict[str, Any]:
    """Sets a tutor's daily and weekly volunteer-minute caps.

    Args:
        tutor_id: The tutor to update.
        daily_cap_minutes: The new daily cap.
        weekly_cap_minutes: The new weekly cap.

    Returns:
        The updated `tutor_profiles` row.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(TUTOR_PROFILES_TABLE)
        .update({"daily_cap_minutes": daily_cap_minutes, "weekly_cap_minutes": weekly_cap_minutes})
        .eq("id", str(tutor_id))
        .execute()
    )
    return result.data[0]
