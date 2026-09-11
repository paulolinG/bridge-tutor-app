from datetime import UTC, datetime

from app.services import diagnostics, sessions

STARTS_AT = datetime(2026, 1, 5, 18, 0, tzinfo=UTC)
ENDS_AT = datetime(2026, 1, 5, 19, 0, tzinfo=UTC)

ITEMS = [
    {"correct_index": 0},
    {"correct_index": 1},
    {"correct_index": 2},
    {"correct_index": 3},
    {"correct_index": 0},
]


def test_score_answers_returns_percent_correct() -> None:
    answers = [0, 1, 2, 0, 3]

    assert diagnostics.score_answers(ITEMS, answers) == 60.0


def test_delta_growth_is_the_percentage_point_difference() -> None:
    assert diagnostics.delta_growth(sessions.COMPLETED, 40.0, 80.0) == 40.0


def test_delta_growth_is_none_when_the_baseline_was_skipped() -> None:
    # Not 0.0: imputing a zero baseline would invent an 80-point gain.
    assert diagnostics.delta_growth(sessions.COMPLETED, None, 80.0) is None


def test_delta_growth_is_none_for_a_session_that_did_not_complete() -> None:
    assert diagnostics.delta_growth(sessions.NO_SHOW, 40.0, 80.0) is None


def test_is_baseline_open_just_before_the_session_starts() -> None:
    now = datetime(2026, 1, 5, 17, 50, tzinfo=UTC)

    assert diagnostics.is_baseline_open(sessions.SCHEDULED, STARTS_AT, ENDS_AT, now) is True


def test_is_exit_ticket_open_once_the_tutor_marks_the_session_completed() -> None:
    # Mid-window: the session is no longer writable, but the exit ticket is
    # precisely what the student is meant to do now.
    now = datetime(2026, 1, 5, 18, 30, tzinfo=UTC)

    assert sessions.is_session_writable(sessions.COMPLETED, STARTS_AT, ENDS_AT, now) is False
    assert diagnostics.is_exit_ticket_open(sessions.COMPLETED, STARTS_AT, ENDS_AT, now) is True


def test_is_exit_ticket_open_after_ends_at_when_the_tutor_forgot_to_end_it() -> None:
    now = datetime(2026, 1, 5, 19, 30, tzinfo=UTC)

    assert diagnostics.is_exit_ticket_open(sessions.SCHEDULED, STARTS_AT, ENDS_AT, now) is True


def test_is_exit_ticket_closed_mid_session_before_it_ends() -> None:
    now = datetime(2026, 1, 5, 18, 30, tzinfo=UTC)

    assert diagnostics.is_exit_ticket_open(sessions.SCHEDULED, STARTS_AT, ENDS_AT, now) is False


def test_is_exit_ticket_closed_for_a_cancelled_session() -> None:
    now = datetime(2026, 1, 5, 19, 30, tzinfo=UTC)

    assert diagnostics.is_exit_ticket_open(sessions.CANCELLED, STARTS_AT, ENDS_AT, now) is False
