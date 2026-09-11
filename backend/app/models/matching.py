from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")
NEUTRAL_ACADEMIC_AVERAGE: float = 70.0
NEUTRAL_MULTIPLIER: float = 1.0


@dataclass(frozen=True, slots=True)
class PendingRequest:
    request_id: UUID
    student_id: UUID
    microtopic_id: UUID
    starts_at: datetime
    duration_minutes: int
    created_at: datetime
    academic_average: float | None
    funding_deficit_multiplier: float | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "PendingRequest":
        """Parses a `session_requests` row with its nested urgency-input embed.

        Args:
            row: A row from `list_pending_requests`, including the nested
                `student_profiles(academic_average, regions(funding_deficit_multiplier))`
                embed. The embed's `regions` sub-object is None when the
                student has no region set.

        Returns:
            The parsed `PendingRequest`.
        """
        student = row["student_profiles"] or {}
        region = student.get("regions") or {}
        return cls(
            request_id=UUID(row["id"]),
            student_id=UUID(row["student_id"]),
            microtopic_id=UUID(row["microtopic_id"]),
            starts_at=datetime.fromisoformat(row["starts_at"]),
            duration_minutes=row["duration_minutes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            academic_average=student.get("academic_average"),
            funding_deficit_multiplier=region.get("funding_deficit_multiplier"),
        )


@dataclass(frozen=True, slots=True)
class RequestWindow:
    day_of_week: int
    start_minute: int
    end_minute: int
    local_date: date
    week_start: date
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    is_schedulable: bool


@dataclass(frozen=True, slots=True)
class AvailabilityWindow:
    day_of_week: int
    start_minute: int
    end_minute: int


@dataclass(frozen=True, slots=True)
class CommittedSession:
    starts_at: datetime
    ends_at: datetime
    local_date: date
    week_start: date
    duration_minutes: int


@dataclass(frozen=True, slots=True)
class TutorCandidate:
    tutor_id: UUID
    daily_cap_minutes: int
    weekly_cap_minutes: int
    availability: tuple[AvailabilityWindow, ...]
    commitments: tuple[CommittedSession, ...]
