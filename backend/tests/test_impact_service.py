from uuid import uuid4

from app.models.impact import TutorSessionRow
from app.services import impact, sessions

STUDENT_A = uuid4()
STUDENT_B = uuid4()
FRACTIONS = "Math: Fractions"


def _session(
    *,
    student_id=STUDENT_A,
    microtopic_label=FRACTIONS,
    status=sessions.COMPLETED,
    duration_minutes=60,
    baseline_percent=None,
    exit_percent=None,
) -> TutorSessionRow:
    return TutorSessionRow(
        session_id=uuid4(),
        student_id=student_id,
        microtopic_label=microtopic_label,
        status=status,
        duration_minutes=duration_minutes,
        baseline_percent=baseline_percent,
        exit_percent=exit_percent,
    )


def test_volunteer_minutes_counts_completed_sessions_only() -> None:
    rows = [
        _session(duration_minutes=60),
        _session(duration_minutes=60, status=sessions.NO_SHOW),
    ]

    result = impact.build_impact(rows)

    assert result.sessions_completed == 1
    assert result.volunteer_minutes == 60


def test_students_helped_counts_each_student_once() -> None:
    rows = [
        _session(student_id=STUDENT_A),
        _session(student_id=STUDENT_A),
        _session(student_id=STUDENT_B),
    ]

    assert impact.build_impact(rows).students_helped == 2


def test_average_delta_growth_reports_how_many_sessions_it_measured() -> None:
    # One measured session (+40), one where the student skipped the baseline.
    rows = [
        _session(baseline_percent=40.0, exit_percent=80.0),
        _session(baseline_percent=None, exit_percent=80.0),
    ]

    entry = impact.build_impact(rows).by_microtopic[0]

    assert entry.microtopic_label == FRACTIONS
    assert entry.average_delta_growth == 40.0
    assert entry.measured_sessions == 1
    assert entry.total_sessions == 2


def test_average_delta_growth_is_none_when_nothing_was_measured() -> None:
    entry = impact.build_impact([_session()]).by_microtopic[0]

    assert entry.average_delta_growth is None
    assert entry.measured_sessions == 0
    assert entry.total_sessions == 1
