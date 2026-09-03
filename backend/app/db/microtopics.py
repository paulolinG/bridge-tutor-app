from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase, run_query


async def list_microtopics() -> list[dict[str, Any]]:
    result = await run_query(
        lambda: get_supabase().table("microtopics").select("*").order("label").execute()
    )
    return result.data


async def get_microtopic(microtopic_id: UUID) -> dict[str, Any] | None:
    result = await run_query(
        lambda: get_supabase()
        .table("microtopics")
        .select("*")
        .eq("id", str(microtopic_id))
        .execute()
    )
    return result.data[0] if result.data else None
