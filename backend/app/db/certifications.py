from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase, run_query
from app.models.message import Message
from app.models.rubric import RubricScore

TABLE = "tutor_certifications"


async def create_certification(
    tutor_id: UUID, microtopic_id: UUID, persona_key: str
) -> dict[str, Any]:
    result = await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .insert(
            {
                "tutor_id": str(tutor_id),
                "microtopic_id": str(microtopic_id),
                "persona_key": persona_key,
                "transcript": [],
            }
        )
        .execute()
    )
    return result.data[0]


async def get_certification(certification_id: UUID) -> dict[str, Any] | None:
    result = await run_query(
        lambda: get_supabase().table(TABLE).select("*").eq("id", str(certification_id)).execute()
    )
    return result.data[0] if result.data else None


async def append_message(
    certification_id: UUID, transcript: list[Message], expected_version: int
) -> bool:
    """Optimistic-concurrency write: only succeeds if the row is still at expected_version.

    Returns False if another request updated the row first (caller should surface a
    conflict to the client rather than silently clobbering the other write).
    """
    result = await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .update(
            {
                "transcript": [message.model_dump(mode="json") for message in transcript],
                "version": expected_version + 1,
            }
        )
        .eq("id", str(certification_id))
        .eq("version", expected_version)
        .execute()
    )
    return len(result.data) > 0


async def mark_completed(certification_id: UUID, score: RubricScore) -> None:
    updates = {
        **score.to_row(),
        "status": "completed",
        "completed_at": datetime.now(UTC).isoformat(),
    }
    await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .update(updates)
        .eq("id", str(certification_id))
        .execute()
    )


async def upsert_competency(tutor_id: UUID, microtopic_id: UUID, certification_id: UUID) -> None:
    await run_query(
        lambda: get_supabase()
        .table("tutor_microtopic_competencies")
        .upsert(
            {
                "tutor_id": str(tutor_id),
                "microtopic_id": str(microtopic_id),
                "certification_id": str(certification_id),
            },
            on_conflict="tutor_id,microtopic_id",
        )
        .execute()
    )


async def update_tutor_certification_status(tutor_id: UUID, status: str) -> None:
    await run_query(
        lambda: get_supabase()
        .table("tutor_profiles")
        .update({"certification_status": status})
        .eq("id", str(tutor_id))
        .execute()
    )
