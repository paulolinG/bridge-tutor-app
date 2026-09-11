from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.routes import diagnostic_common, session_common
from app.core import daily
from app.db import sessions as sessions_db
from app.models.diagnostic import (
    CurrentDiagnosticResponse,
    DiagnosticKind,
    SubmitDiagnosticRequest,
    SubmitDiagnosticResponse,
)
from app.models.session import (
    CallCredentialsResponse,
    PostMessageRequest,
    PutWhiteboardRequest,
    SessionInfoResponse,
    SessionMessageResponse,
    WhiteboardResponse,
)
from app.services import sessions as sessions_service

router = APIRouter(prefix="/join", tags=["join"])

SESSION_NOT_FOUND_DETAIL: str = "Session not found"
JOIN_NOT_OPEN_DETAIL: str = "This session cannot be joined right now"
CALL_UNAVAILABLE_DETAIL: str = "Video call service is temporarily unavailable, please try again"

DAILY_ROOM_EXP_BUFFER_MINUTES: int = sessions_service.JOIN_CLOSES_AFTER_MINUTES


def _room_name(session_id: UUID) -> str:
    return f"bridge-{session_id}"


async def _get_or_create_room(session_id: UUID, room_name: str | None, room_exp: datetime) -> str:
    """Returns the session's Daily room, creating it lazily on first join."""
    if room_name is not None:
        return room_name
    room_name = _room_name(session_id)
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


@router.get("/{join_token}")
async def get_join_info(join_token: str) -> SessionInfoResponse:
    """Public lookup for the join-link page. 200 even outside the join
    window, so an early student sees the scheduled time rather than a 403."""
    row = await sessions_db.get_by_join_token(join_token)
    if row is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_DETAIL)

    starts_at = datetime.fromisoformat(row["starts_at"])
    ends_at = datetime.fromisoformat(row["ends_at"])
    return SessionInfoResponse(
        id=UUID(row["id"]),
        microtopic_label=row["session_requests"]["microtopics"]["label"],
        starts_at=starts_at,
        ends_at=ends_at,
        status=row["status"],
        join_open=sessions_service.is_join_open(starts_at, ends_at, datetime.now(UTC)),
    )


@router.post("/{join_token}/call")
async def get_student_call_credentials(join_token: str) -> CallCredentialsResponse:
    """Mints the student's meeting token, creating the Daily room lazily on
    first join. 403 outside the join window."""
    row = await sessions_db.get_by_join_token(join_token)
    if row is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_DETAIL)

    starts_at = datetime.fromisoformat(row["starts_at"])
    ends_at = datetime.fromisoformat(row["ends_at"])
    if not sessions_service.is_join_open(starts_at, ends_at, datetime.now(UTC)):
        raise HTTPException(status_code=403, detail=JOIN_NOT_OPEN_DETAIL)

    room_exp = ends_at + timedelta(minutes=DAILY_ROOM_EXP_BUFFER_MINUTES)
    room_name = await _get_or_create_room(UUID(row["id"]), row["daily_room_name"], room_exp)
    return await _mint_call_credentials(room_name, "Student", is_owner=False, exp=room_exp)


async def _get_session_or_404(join_token: str) -> dict:
    row = await sessions_db.get_by_join_token(join_token)
    if row is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_DETAIL)
    return row


@router.get("/{join_token}/messages")
async def list_join_messages(join_token: str) -> list[SessionMessageResponse]:
    row = await _get_session_or_404(join_token)
    return await session_common.list_messages(row)


@router.post("/{join_token}/messages")
async def post_join_message(join_token: str, body: PostMessageRequest) -> SessionMessageResponse:
    row = await _get_session_or_404(join_token)
    return await session_common.post_message(row, "student", body)


@router.get("/{join_token}/whiteboard")
async def get_join_whiteboard(join_token: str) -> WhiteboardResponse:
    row = await _get_session_or_404(join_token)
    return await session_common.get_whiteboard(row)


@router.put("/{join_token}/whiteboard")
async def put_join_whiteboard(join_token: str, body: PutWhiteboardRequest) -> WhiteboardResponse:
    row = await _get_session_or_404(join_token)
    return await session_common.put_whiteboard(row, body)


@router.get("/{join_token}/diagnostic")
async def get_join_diagnostic(join_token: str) -> CurrentDiagnosticResponse:
    """The diagnostic the student should answer now, answer key stripped."""
    row = await _get_session_or_404(join_token)
    return await diagnostic_common.current_diagnostic(row)


@router.post("/{join_token}/diagnostic/baseline/skip")
async def skip_join_baseline(join_token: str) -> SubmitDiagnosticResponse:
    """Declines the baseline. Permanent — it is never offered again."""
    row = await _get_session_or_404(join_token)
    return await diagnostic_common.skip_baseline(row)


@router.post("/{join_token}/diagnostic/{kind}")
async def submit_join_diagnostic(
    join_token: str, kind: DiagnosticKind, body: SubmitDiagnosticRequest
) -> SubmitDiagnosticResponse:
    row = await _get_session_or_404(join_token)
    return await diagnostic_common.submit_diagnostic(row, kind, body)
