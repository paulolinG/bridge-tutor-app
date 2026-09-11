from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.supabase import get_supabase, run_query
from app.models.diagnostic import BASELINE, EXIT

TABLE = "session_diagnostic_forms"

DiagnosticItems = list[dict[str, Any]]


async def create_pair(
    session_id: UUID, baseline_items: DiagnosticItems, exit_items: DiagnosticItems
) -> None:
    """Stores a generated matched pair as the session's two forms.

    Args:
        session_id: The session the pair belongs to.
        baseline_items: The Baseline Diagnostic's items, answer key included.
        exit_items: The Exit Ticket's items, answer key included.
    """
    await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .insert(
            [
                {"session_id": str(session_id), "kind": BASELINE, "items": baseline_items},
                {"session_id": str(session_id), "kind": EXIT, "items": exit_items},
            ]
        )
        .execute()
    )


async def get_forms(session_id: UUID) -> list[dict[str, Any]]:
    """Fetches both of a session's diagnostic forms.

    Args:
        session_id: The session whose forms to fetch.

    Returns:
        The form rows, empty if generation hasn't run for this session.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .select("kind, items, answers, score_percent, skipped")
        .eq("session_id", str(session_id))
        .execute()
    )
    return result.data or []


async def submit_answers(
    session_id: UUID, kind: str, answers: list[int], score_percent: float
) -> bool:
    """Records a student's answers, once and only once.

    Args:
        session_id: The session the form belongs to.
        kind: Which form — 'baseline' or 'exit'.
        answers: The chosen option index per item.
        score_percent: The deterministically computed score.

    Returns:
        True if this call recorded the submission, False if answers were
        already present — a reload or a double-tap must never overwrite a
        measurement that has already been taken.
    """
    result = await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .update(
            {
                "answers": answers,
                "score_percent": score_percent,
                "submitted_at": datetime.now(UTC).isoformat(),
            }
        )
        .eq("session_id", str(session_id))
        .eq("kind", kind)
        .is_("answers", "null")
        .execute()
    )
    return len(result.data) > 0


async def mark_skipped(session_id: UUID) -> None:
    """Records that the student declined the Baseline Diagnostic.

    Permanent: the baseline is offered once, before the session. Answering it
    afterwards, having just been taught the material, would make Delta Growth
    meaningless.

    Args:
        session_id: The session whose baseline was skipped.
    """
    await run_query(
        lambda: get_supabase()
        .table(TABLE)
        .update({"skipped": True})
        .eq("session_id", str(session_id))
        .eq("kind", BASELINE)
        .is_("answers", "null")
        .execute()
    )


async def list_session_ids_missing_forms(now: datetime, limit: int) -> list[dict[str, Any]]:
    """Finds upcoming scheduled sessions that have no diagnostics yet.

    Args:
        now: The current time — only future sessions are worth generating for.
        limit: Hard ceiling on how many to return, so a persistent failure
            can never turn into an unbounded number of AI calls per run.

    Returns:
        Session rows carrying the microtopic and student grade level needed
        to generate their pair.
    """
    result = await run_query(
        lambda: get_supabase()
        .table("sessions")
        .select(
            "id, session_requests(microtopic_id, microtopics(label, concepts),"
            " student_profiles(grade_level)), session_diagnostic_forms(id)"
        )
        .eq("status", "scheduled")
        .gte("starts_at", now.isoformat())
        .order("starts_at")
        .execute()
    )
    missing = [row for row in (result.data or []) if not row.get("session_diagnostic_forms")]
    return missing[:limit]


async def set_microtopic_concepts(microtopic_id: UUID, concepts: list[str]) -> None:
    """Backfills a coordinator-added microtopic's concept blueprint.

    Fixing the blueprint on first use is what keeps every later session on
    that microtopic measuring the same five concepts.

    Args:
        microtopic_id: The microtopic to backfill.
        concepts: The five concepts its diagnostics measure.
    """
    await run_query(
        lambda: get_supabase()
        .table("microtopics")
        .update({"concepts": concepts})
        .eq("id", str(microtopic_id))
        .execute()
    )
