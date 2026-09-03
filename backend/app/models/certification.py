from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.message import Message
from app.models.rubric import RubricScore


class StartCertificationRequest(BaseModel):
    microtopic_id: UUID


class StartCertificationResponse(BaseModel):
    certification_id: UUID
    student_facing_blurb: str
    opening_message: str
    min_turns_to_end: int
    max_turns: int


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("content cannot be blank")
        return stripped


class SendMessageResponse(BaseModel):
    reply: str
    turn_count: int


class EndCertificationResponse(BaseModel):
    score: RubricScore


class CertificationStateResponse(BaseModel):
    certification_id: UUID
    status: Literal["in_progress", "completed"]
    transcript: list[Message]
    tutor_turn_count: int
    score: RubricScore | None = None
    min_turns_to_end: int
    max_turns: int
