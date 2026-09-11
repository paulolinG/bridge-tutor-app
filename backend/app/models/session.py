from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

MESSAGE_MAX_LENGTH: int = 2000


class UpcomingSessionResponse(BaseModel):
    id: UUID
    microtopic_label: str
    starts_at: datetime
    ends_at: datetime
    join_token: str


class SessionInfoResponse(BaseModel):
    """Returned by the public join-link lookup. Never carries the room URL —
    that's only handed out once the join window is actually open."""

    id: UUID
    microtopic_label: str
    starts_at: datetime
    ends_at: datetime
    status: str
    join_open: bool


class CallCredentialsResponse(BaseModel):
    room_url: str
    token: str


class UpdateSessionStatusRequest(BaseModel):
    status: Literal["completed", "no_show", "cancelled"]


class SessionMessageResponse(BaseModel):
    id: UUID
    sender_role: Literal["tutor", "student"]
    content: str
    created_at: datetime


class PostMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=MESSAGE_MAX_LENGTH)


class WhiteboardResponse(BaseModel):
    snapshot: dict[str, Any] | None


class PutWhiteboardRequest(BaseModel):
    snapshot: dict[str, Any] | None
