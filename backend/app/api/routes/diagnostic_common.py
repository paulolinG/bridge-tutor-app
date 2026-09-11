from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.db import diagnostics as diagnostics_db
from app.models.diagnostic import (
    BASELINE,
    EXIT,
    CurrentDiagnosticResponse,
    DiagnosticFormResponse,
    DiagnosticItemResponse,
    SubmitDiagnosticRequest,
    SubmitDiagnosticResponse,
)
from app.services import diagnostics as diagnostics_service

DIAGNOSTIC_NOT_OPEN_DETAIL: str = "This diagnostic is not open right now"
ALREADY_SUBMITTED_DETAIL: str = "This diagnostic has already been submitted"

SessionRow = dict[str, Any]


def _window(row: SessionRow) -> tuple[str, datetime, datetime, datetime]:
    return (
        row["status"],
        datetime.fromisoformat(row["starts_at"]),
        datetime.fromisoformat(row["ends_at"]),
        datetime.now(UTC),
    )


def _is_open(row: SessionRow, kind: str) -> bool:
    status, starts_at, ends_at, now = _window(row)
    if kind == BASELINE:
        return diagnostics_service.is_baseline_open(status, starts_at, ends_at, now)
    return diagnostics_service.is_exit_ticket_open(status, starts_at, ends_at, now)


def _is_outstanding(form: dict[str, Any]) -> bool:
    return form["answers"] is None and not form["skipped"]


def _to_response(form: dict[str, Any]) -> DiagnosticFormResponse:
    """Projects a stored form into the student's view, dropping the answer key."""
    return DiagnosticFormResponse(
        kind=form["kind"],
        items=[
            DiagnosticItemResponse(prompt=item["prompt"], options=item["options"])
            for item in form["items"]
        ],
    )


async def current_diagnostic(row: SessionRow) -> CurrentDiagnosticResponse:
    """The form the student should be shown right now, if any.

    The baseline takes precedence before the session; the exit ticket becomes
    available once the tutor ends the session or `ends_at` passes.
    """
    forms = {form["kind"]: form for form in await diagnostics_db.get_forms(UUID(row["id"]))}
    for kind in (BASELINE, EXIT):
        form = forms.get(kind)
        if form is not None and _is_outstanding(form) and _is_open(row, kind):
            return CurrentDiagnosticResponse(form=_to_response(form))
    return CurrentDiagnosticResponse(form=None)


async def submit_diagnostic(
    row: SessionRow, kind: str, body: SubmitDiagnosticRequest
) -> SubmitDiagnosticResponse:
    """Scores and records a submission, refusing a second one.

    Raises:
        HTTPException: 403 if this form isn't open, 404 if it was never
            generated, 409 if answers are already recorded.
    """
    session_id = UUID(row["id"])
    if not _is_open(row, kind):
        raise HTTPException(status_code=403, detail=DIAGNOSTIC_NOT_OPEN_DETAIL)

    forms = {form["kind"]: form for form in await diagnostics_db.get_forms(session_id)}
    form = forms.get(kind)
    if form is None:
        raise HTTPException(status_code=404, detail="No diagnostic exists for this session")

    score = diagnostics_service.score_answers(form["items"], body.answers)
    wrote = await diagnostics_db.submit_answers(session_id, kind, body.answers, score)
    if not wrote:
        raise HTTPException(status_code=409, detail=ALREADY_SUBMITTED_DETAIL)

    return SubmitDiagnosticResponse(submitted=True)


async def skip_baseline(row: SessionRow) -> SubmitDiagnosticResponse:
    """Records a permanent skip, so the baseline is never offered again."""
    if not _is_open(row, BASELINE):
        raise HTTPException(status_code=403, detail=DIAGNOSTIC_NOT_OPEN_DETAIL)
    await diagnostics_db.mark_skipped(UUID(row["id"]))
    return SubmitDiagnosticResponse(submitted=False)
