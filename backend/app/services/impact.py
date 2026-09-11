from collections import defaultdict

from app.models.impact import MicrotopicImpact, TutorImpactResponse, TutorSessionRow
from app.services.diagnostics import delta_growth
from app.services.sessions import COMPLETED


def _by_microtopic(completed: list[TutorSessionRow]) -> list[MicrotopicImpact]:
    """Groups completed sessions by microtopic, averaging the measured deltas.

    Every average is reported alongside the number of sessions it was
    measured from: an average built from one session must never be readable
    as one built from fifty.
    """
    grouped: dict[str, list[TutorSessionRow]] = defaultdict(list)
    for row in completed:
        grouped[row.microtopic_label].append(row)

    entries: list[MicrotopicImpact] = []
    for label, rows in sorted(grouped.items()):
        deltas = [
            delta
            for row in rows
            if (delta := delta_growth(row.status, row.baseline_percent, row.exit_percent))
            is not None
        ]
        entries.append(
            MicrotopicImpact(
                microtopic_label=label,
                average_delta_growth=sum(deltas) / len(deltas) if deltas else None,
                measured_sessions=len(deltas),
                total_sessions=len(rows),
            )
        )
    return entries


def build_impact(rows: list[TutorSessionRow]) -> TutorImpactResponse:
    """Aggregates a tutor's sessions into their volunteer impact record.

    Args:
        rows: Every session belonging to the tutor, in any status.

    Returns:
        Counts derived from `completed` sessions only — a session the student
        never attended is not tutoring delivered.
    """
    completed = [row for row in rows if row.status == COMPLETED]
    return TutorImpactResponse(
        sessions_completed=len(completed),
        volunteer_minutes=sum(row.duration_minutes for row in completed),
        students_helped=len({row.student_id for row in completed}),
        by_microtopic=_by_microtopic(completed),
    )
