from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MatchedSession:
    """A `sessions` row not yet reported in a Coordinator Digest."""

    session_id: UUID
    join_token: str
    student_display_name: str
    student_phone_number: str
    microtopic_label: str
    starts_at: datetime

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "MatchedSession":
        request = row["session_requests"]
        student = request["student_profiles"]
        return cls(
            session_id=UUID(row["id"]),
            join_token=row["join_token"],
            student_display_name=student["display_name"],
            student_phone_number=student["phone_number"],
            microtopic_label=request["microtopics"]["label"],
            starts_at=datetime.fromisoformat(row["starts_at"]),
        )


@dataclass(frozen=True, slots=True)
class ExpiredRequest:
    """A `session_requests` row not yet reported in a Coordinator Digest."""

    request_id: UUID
    student_display_name: str
    student_phone_number: str
    microtopic_label: str
    starts_at: datetime

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ExpiredRequest":
        student = row["student_profiles"]
        return cls(
            request_id=UUID(row["id"]),
            student_display_name=student["display_name"],
            student_phone_number=student["phone_number"],
            microtopic_label=row["microtopics"]["label"],
            starts_at=datetime.fromisoformat(row["starts_at"]),
        )
