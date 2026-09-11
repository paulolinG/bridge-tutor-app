from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.db import session_messages as session_messages_db
from app.db import sessions as sessions_db
from app.models.session import (
    PostMessageRequest,
    PutWhiteboardRequest,
    SessionMessageResponse,
    WhiteboardResponse,
)
from app.services import sessions as sessions_service

SESSION_NOT_WRITABLE_DETAIL: str = "This session is not currently open for messages"

SessionRow = dict[str, Any]


def ensure_writable(row: SessionRow) -> None:
    """Raises 403 unless the session currently accepts chat/whiteboard writes."""
    starts_at = datetime.fromisoformat(row["starts_at"])
    ends_at = datetime.fromisoformat(row["ends_at"])
    writable = sessions_service.is_session_writable(
        row["status"], starts_at, ends_at, datetime.now(UTC)
    )
    if not writable:
        raise HTTPException(status_code=403, detail=SESSION_NOT_WRITABLE_DETAIL)


async def list_messages(row: SessionRow) -> list[SessionMessageResponse]:
    rows = await session_messages_db.list_messages(UUID(row["id"]))
    return [
        SessionMessageResponse(
            id=message["id"],
            sender_role=message["sender_role"],
            content=message["content"],
            created_at=message["created_at"],
        )
        for message in rows
    ]


async def post_message(
    row: SessionRow, sender_role: str, body: PostMessageRequest
) -> SessionMessageResponse:
    ensure_writable(row)
    created = await session_messages_db.create_message(UUID(row["id"]), sender_role, body.content)
    return SessionMessageResponse(
        id=created["id"],
        sender_role=created["sender_role"],
        content=created["content"],
        created_at=created["created_at"],
    )


async def get_whiteboard(row: SessionRow) -> WhiteboardResponse:
    return WhiteboardResponse(snapshot=row.get("whiteboard_snapshot"))


async def put_whiteboard(row: SessionRow, body: PutWhiteboardRequest) -> WhiteboardResponse:
    ensure_writable(row)
    await sessions_db.set_whiteboard_snapshot(UUID(row["id"]), body.snapshot)
    return WhiteboardResponse(snapshot=body.snapshot)
