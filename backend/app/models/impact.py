from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel

BASELINE: str = "baseline"
EXIT: str = "exit"


@dataclass(frozen=True, slots=True)
class TutorSessionRow:
    """One of a tutor's sessions, flattened from its Supabase embeds."""

    session_id: UUID
    student_id: UUID
    microtopic_label: str
    status: str
    duration_minutes: int
    baseline_percent: float | None
    exit_percent: float | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "TutorSessionRow":
        request = row["session_requests"]
        scores = {
            form["kind"]: form["score_percent"]
            for form in row.get("session_diagnostic_forms") or []
        }
        return cls(
            session_id=UUID(row["id"]),
            student_id=UUID(request["student_id"]),
            microtopic_label=request["microtopics"]["label"],
            status=row["status"],
            duration_minutes=request["duration_minutes"],
            baseline_percent=scores.get(BASELINE),
            exit_percent=scores.get(EXIT),
        )


class MicrotopicImpact(BaseModel):
    microtopic_label: str
    average_delta_growth: float | None
    measured_sessions: int
    total_sessions: int


class TutorImpactResponse(BaseModel):
    sessions_completed: int
    volunteer_minutes: int
    students_helped: int
    by_microtopic: list[MicrotopicImpact]
