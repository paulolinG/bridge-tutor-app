from datetime import UTC, datetime

from app.services import sessions

STARTS_AT = datetime(2026, 1, 5, 18, 0, tzinfo=UTC)
ENDS_AT = datetime(2026, 1, 5, 19, 0, tzinfo=UTC)


def test_is_join_open_true_during_the_session() -> None:
    now = datetime(2026, 1, 5, 18, 30, tzinfo=UTC)

    assert sessions.is_join_open(STARTS_AT, ENDS_AT, now) is True


def test_is_join_open_true_exactly_fifteen_minutes_before_start() -> None:
    now = datetime(2026, 1, 5, 17, 45, tzinfo=UTC)

    assert sessions.is_join_open(STARTS_AT, ENDS_AT, now) is True


def test_is_join_open_false_one_minute_before_the_open_boundary() -> None:
    now = datetime(2026, 1, 5, 17, 44, tzinfo=UTC)

    assert sessions.is_join_open(STARTS_AT, ENDS_AT, now) is False


def test_is_join_open_true_exactly_three_hours_after_end() -> None:
    now = datetime(2026, 1, 5, 22, 0, tzinfo=UTC)

    assert sessions.is_join_open(STARTS_AT, ENDS_AT, now) is True


def test_is_join_open_false_one_minute_after_the_close_boundary() -> None:
    now = datetime(2026, 1, 5, 22, 1, tzinfo=UTC)

    assert sessions.is_join_open(STARTS_AT, ENDS_AT, now) is False


def test_can_transition_scheduled_to_completed() -> None:
    assert sessions.can_transition(sessions.SCHEDULED, sessions.COMPLETED) is True


def test_can_transition_rejects_leaving_a_terminal_status() -> None:
    assert sessions.can_transition(sessions.COMPLETED, sessions.NO_SHOW) is False


def test_is_session_writable_true_for_scheduled_session_inside_window() -> None:
    now = datetime(2026, 1, 5, 18, 30, tzinfo=UTC)

    assert sessions.is_session_writable(sessions.SCHEDULED, STARTS_AT, ENDS_AT, now) is True


def test_is_session_writable_false_once_completed() -> None:
    now = datetime(2026, 1, 5, 18, 30, tzinfo=UTC)

    assert sessions.is_session_writable(sessions.COMPLETED, STARTS_AT, ENDS_AT, now) is False


def test_is_session_writable_false_outside_the_join_window() -> None:
    now = datetime(2026, 1, 5, 23, 0, tzinfo=UTC)

    assert sessions.is_session_writable(sessions.SCHEDULED, STARTS_AT, ENDS_AT, now) is False
