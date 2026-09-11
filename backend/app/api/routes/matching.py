import random
import secrets
from collections import defaultdict
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException

from app.core import email
from app.core.config import get_settings
from app.db import diagnostics as diagnostics_db
from app.db import matching as matching_db
from app.db import notifications as notifications_db
from app.models.diagnostic import BASELINE, DEFAULT_GRADE_LEVEL, EXIT
from app.models.matching import TORONTO, CommittedSession, PendingRequest
from app.models.notification import ExpiredRequest, MatchedSession
from app.services import matching as matching_service
from app.services import notifications as notifications_service
from app.services.diagnostic_generation import generate_blueprint, generate_pair

router = APIRouter(prefix="/internal/matching", tags=["matching"])

DAYS_PER_WEEK: int = 7

# Ceiling on AI calls per run. Without it, a failure mode that never resolves
# would generate one call per pending session every hour, forever. Sessions
# are at least two hours out, so anything over the cap simply waits for the
# next run.
MAX_DIAGNOSTIC_GENERATIONS_PER_RUN: int = 20


def get_rng() -> random.Random:
    return random.Random()


def _verify_secret(x_matching_secret: str | None = Header(default=None)) -> None:
    """Guards the batch-run endpoint with a shared secret.

    Raises:
        HTTPException: 503 if `MATCHING_SECRET` isn't configured (so a
            misconfigured deploy is never left wide open), 401 if the header
            is missing or doesn't match.
    """
    settings = get_settings()
    if not settings.matching_secret:
        raise HTTPException(status_code=503, detail="Matching engine is not configured")
    if x_matching_secret is None or not secrets.compare_digest(
        x_matching_secret, settings.matching_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing matching secret")


@router.post("/run")
async def run_matching(
    x_matching_secret: str | None = Header(default=None),
) -> dict[str, int]:
    """Runs one batch-matching cycle: expires stale requests, then matches the rest.

    Guarded by the `X-Matching-Secret` header, intended to be called hourly by
    `pg_cron`/`pg_net`. Idempotent within the same hour: a request that has
    already been matched or expired is no longer `pending` and won't be
    reprocessed by a second call.

    Returns:
        Counts of expired, processed, and matched requests for this run.
    """
    _verify_secret(x_matching_secret)

    now = datetime.now(UTC)
    expired = await matching_db.expire_stale_requests(now)

    rows = await matching_db.list_pending_requests()
    requests = matching_service.order_requests([PendingRequest.from_row(row) for row in rows])

    rng = get_rng()
    ledger: dict[object, list[CommittedSession]] = defaultdict(list)
    processed = 0
    matched = 0

    for request in requests:
        processed += 1
        window = matching_service.to_request_window(request.starts_at, request.duration_minutes)
        if not window.is_schedulable:
            continue

        range_start, range_end = _candidate_fetch_range(window.week_start)
        candidates = await matching_db.list_candidates(
            request.microtopic_id, range_start, range_end
        )
        candidates = [
            _with_in_batch_commitments(candidate, ledger[candidate.tutor_id])
            for candidate in candidates
        ]

        tutor_id = matching_service.select_match(candidates, window, rng)
        if tutor_id is None:
            continue

        if not await matching_db.claim_request(request.request_id):
            continue

        await matching_db.create_session(
            request.request_id, tutor_id, window.starts_at, window.ends_at
        )
        ledger[tutor_id].append(
            matching_service.to_committed_session(window.starts_at, window.ends_at)
        )
        matched += 1

    generated = await _generate_missing_diagnostics(now)
    notified = await _send_coordinator_digest()

    return {
        "expired": expired,
        "processed": processed,
        "matched": matched,
        "diagnostics_generated": generated,
        "notified": notified,
    }


async def _send_coordinator_digest() -> int:
    """Emails the Coordinator Digest for everything not yet reported.

    Send-then-stamp, all-or-nothing: stamping optimistically before the send
    would lose matches on any failure, and a failed send here must never
    take down a run that has already committed real matches — it simply
    means the next hourly run retries the same outstanding items.

    Returns:
        How many matches and expirations the digest covered, 0 if there was
        nothing outstanding, notification is unconfigured, or the send
        failed.
    """
    settings = get_settings()
    if not settings.coordinator_email or not settings.resend_api_key:
        return 0

    match_rows = await notifications_db.list_unnotified_matches()
    expiration_rows = await notifications_db.list_unnotified_expirations()
    matches = [MatchedSession.from_row(row) for row in match_rows]
    expirations = [ExpiredRequest.from_row(row) for row in expiration_rows]

    digest = notifications_service.build_digest(matches, expirations, settings.frontend_origin)
    if digest is None:
        return 0

    try:
        await email.send_email(settings.coordinator_email, digest.subject, digest.body)
    except Exception:
        return 0

    await notifications_db.mark_notified(
        [match.session_id for match in matches],
        [expiration.request_id for expiration in expirations],
    )
    return len(matches) + len(expirations)


async def _generate_diagnostics_for(row: dict) -> None:
    """Generates and stores one session's matched Baseline/Exit pair."""
    request = row["session_requests"]
    microtopic = request["microtopics"]
    student = request.get("student_profiles") or {}
    grade_level = student.get("grade_level") or DEFAULT_GRADE_LEVEL

    concepts = microtopic.get("concepts")
    if not concepts:
        blueprint = await generate_blueprint(microtopic["label"], grade_level)
        concepts = blueprint.concepts
        await diagnostics_db.set_microtopic_concepts(UUID(request["microtopic_id"]), concepts)

    pair = await generate_pair(microtopic["label"], concepts, grade_level)
    await diagnostics_db.create_pair(
        UUID(row["id"]), pair.items_for(BASELINE), pair.items_for(EXIT)
    )


async def _generate_missing_diagnostics(now: datetime) -> int:
    """Fills in diagnostics for upcoming sessions that have none yet.

    Covers sessions matched moments ago in this same run, and retries any
    session whose earlier generation failed. A failure here is deliberately
    swallowed: the session simply has no diagnostic and its Delta Growth is
    null, which must never take down a matching run that has already
    committed real matches.

    Args:
        now: The current time — only future sessions are worth generating for.

    Returns:
        How many sessions had a pair generated this run.
    """
    rows = await diagnostics_db.list_session_ids_missing_forms(
        now, MAX_DIAGNOSTIC_GENERATIONS_PER_RUN
    )

    generated = 0
    for row in rows:
        try:
            await _generate_diagnostics_for(row)
        except Exception:
            continue
        generated += 1
    return generated


def _candidate_fetch_range(week_start) -> tuple[datetime, datetime]:
    """Bounds the existing-sessions fetch to comfortably cover a local week.

    Padded by a day on each side so DST or any off-by-a-few-hours drift
    between UTC and America/Toronto can never exclude a relevant session —
    exact day/week attribution still happens per-row via
    `to_committed_session`, this range only limits what's fetched.
    """
    local_midnight = datetime.combine(week_start, datetime.min.time(), tzinfo=TORONTO)
    range_start = (local_midnight - timedelta(days=1)).astimezone(UTC)
    range_end = (local_midnight + timedelta(days=DAYS_PER_WEEK + 1)).astimezone(UTC)
    return range_start, range_end


def _with_in_batch_commitments(candidate, extra_commitments: list[CommittedSession]):
    if not extra_commitments:
        return candidate
    return replace(candidate, commitments=candidate.commitments + tuple(extra_commitments))
