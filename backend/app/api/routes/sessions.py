from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_tutor
from app.api.routes import session_common
from app.core import daily
from app.db import diagnostics as diagnostics_db
from app.db import matching as matching_db
from app.db import sessions as sessions_db
from app.models.diagnostic import BASELINE, BaselineScoreResponse
from app.models.session import (
    CallCredentialsResponse,
    PostMessageRequest,
    PutWhiteboardRequest,
    SessionMessageResponse,
    UpcomingSessionResponse,
    UpdateSessionStatusRequest,
    WhiteboardResponse,
)
from app.services import sessions as sessions_service

router = APIRouter(prefix="/tutors/me/sessions", tags=["sessions"])

SESSION_NOT_FOUND_DETAIL: str = "Session not found"
SESSION_ALREADY_TERMINAL_DETAIL: str = "Session already has a final status"
CALL_UNAVAILABLE_DETAIL: str = "Video call service is temporarily unavailable, please try again"
DAILY_ROOM_EXP_BUFFER_MINUTES: int = sessions_service.JOIN_CLOSES_AFTER_MINUTES


async def _get_or_create_room(session_id: UUID, room_name: str | None, room_exp: datetime) -> str:
    """Returns the session's Daily room, creating it lazily on first join."""
    if room_name is not None:
        return room_name
    room_name = f"bridge-{session_id}"
    try:
        await daily.create_room(room_name, room_exp)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=CALL_UNAVAILABLE_DETAIL) from exc
    await sessions_db.set_daily_room_name(session_id, room_name)
    return room_name


async def _mint_call_credentials(
    room_name: str, user_name: str, is_owner: bool, exp: datetime
) -> CallCredentialsResponse:
    try:
        token = await daily.create_meeting_token(
            room_name=room_name, user_name=user_name, is_owner=is_owner, exp=exp
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=CALL_UNAVAILABLE_DETAIL) from exc
    return CallCredentialsResponse(room_url=daily.room_url(room_name), token=token)


@router.get("")
async def list_my_sessions(
    tutor_id: UUID = Depends(get_current_tutor),
) -> list[UpcomingSessionResponse]:
    rows = await matching_db.list_upcoming_sessions(tutor_id, datetime.now(UTC))
    return [
        UpcomingSessionResponse(
            id=row["id"],
            microtopic_label=row["session_requests"]["microtopics"]["label"],
            starts_at=row["starts_at"],
            ends_at=row["ends_at"],
            join_token=row["join_token"],
        )
        for row in rows
    ]


@router.post("/{session_id}/call")
async def get_tutor_call_credentials(
    session_id: UUID, tutor_id: UUID = Depends(get_current_tutor)
) -> CallCredentialsResponse:
    """Mints the tutor's meeting token, creating the Daily room lazily on
    first join. 404 when the session doesn't belong to this tutor."""
    row = await sessions_db.get_for_tutor(session_id, tutor_id)
    if row is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_DETAIL)

    ends_at = datetime.fromisoformat(row["ends_at"])
    room_exp = ends_at + timedelta(minutes=DAILY_ROOM_EXP_BUFFER_MINUTES)
    room_name = await _get_or_create_room(session_id, row["daily_room_name"], room_exp)
    return await _mint_call_credentials(room_name, "Tutor", is_owner=True, exp=room_exp)


async def _get_session_for_tutor_or_404(session_id: UUID, tutor_id: UUID) -> dict:
    row = await sessions_db.get_for_tutor(session_id, tutor_id)
    if row is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_DETAIL)
    return row


@router.get("/{session_id}/messages")
async def list_tutor_messages(
    session_id: UUID, tutor_id: UUID = Depends(get_current_tutor)
) -> list[SessionMessageResponse]:
    row = await _get_session_for_tutor_or_404(session_id, tutor_id)
    return await session_common.list_messages(row)


@router.post("/{session_id}/messages")
async def post_tutor_message(
    session_id: UUID,
    body: PostMessageRequest,
    tutor_id: UUID = Depends(get_current_tutor),
) -> SessionMessageResponse:
    row = await _get_session_for_tutor_or_404(session_id, tutor_id)
    return await session_common.post_message(row, "tutor", body)


@router.get("/{session_id}/whiteboard")
async def get_tutor_whiteboard(
    session_id: UUID, tutor_id: UUID = Depends(get_current_tutor)
) -> WhiteboardResponse:
    row = await _get_session_for_tutor_or_404(session_id, tutor_id)
    return await session_common.get_whiteboard(row)


@router.put("/{session_id}/whiteboard")
async def put_tutor_whiteboard(
    session_id: UUID,
    body: PutWhiteboardRequest,
    tutor_id: UUID = Depends(get_current_tutor),
) -> WhiteboardResponse:
    row = await _get_session_for_tutor_or_404(session_id, tutor_id)
    return await session_common.put_whiteboard(row, body)


@router.patch("/{session_id}")
async def update_session_status(
    session_id: UUID,
    body: UpdateSessionStatusRequest,
    tutor_id: UUID = Depends(get_current_tutor),
) -> dict[str, str]:
    """Sets a session's terminal status. 409 when it's already terminal."""
    now = datetime.now(UTC)
    updated = await sessions_db.set_status(session_id, tutor_id, body.status, now)
    if not updated:
        raise HTTPException(status_code=409, detail=SESSION_ALREADY_TERMINAL_DETAIL)
    return {"status": body.status}


@router.get("/{session_id}/baseline-score")
async def get_session_baseline_score(
    session_id: UUID, tutor_id: UUID = Depends(get_current_tutor)
) -> BaselineScoreResponse:
    """The student's Baseline Diagnostic score — the number only.

    The items are never exposed to the tutor: the two forms share a
    blueprint, so seeing the baseline is effectively seeing the exit ticket,
    and a tutor who teaches to it inflates their own impact record.
    """
    await _get_session_for_tutor_or_404(session_id, tutor_id)
    forms = await diagnostics_db.get_forms(session_id)
    baseline = next((form for form in forms if form["kind"] == BASELINE), None)
    return BaselineScoreResponse(score_percent=baseline["score_percent"] if baseline else None)
