from datetime import UTC, datetime
from uuid import uuid4

from app.models.notification import ExpiredRequest, MatchedSession
from app.services import notifications

FRONTEND_ORIGIN = "https://bridge.example"


def test_build_digest_is_none_for_no_matches_and_no_expirations() -> None:
    assert notifications.build_digest([], [], FRONTEND_ORIGIN) is None


def test_a_match_line_carries_enough_to_act_on() -> None:
    match = MatchedSession(
        session_id=uuid4(),
        join_token="abc123",
        student_display_name="Ada Lovelace",
        student_phone_number="+15550001111",
        microtopic_label="Math: Fractions",
        starts_at=datetime(2026, 1, 5, 21, 0, tzinfo=UTC),  # 4pm Toronto (EST)
    )

    digest = notifications.build_digest([match], [], FRONTEND_ORIGIN)

    assert digest is not None
    assert "Ada Lovelace" in digest.body
    assert "+15550001111" in digest.body
    assert "Math: Fractions" in digest.body
    assert "4:00 PM" in digest.body
    assert f"{FRONTEND_ORIGIN}/join/abc123" in digest.body


def _match(**overrides) -> MatchedSession:
    defaults = dict(
        session_id=uuid4(),
        join_token="tok",
        student_display_name="Ada Lovelace",
        student_phone_number="+15550001111",
        microtopic_label="Math: Fractions",
        starts_at=datetime(2026, 1, 5, 21, 0, tzinfo=UTC),
    )
    return MatchedSession(**{**defaults, **overrides})


def _expiration(**overrides) -> ExpiredRequest:
    defaults = dict(
        request_id=uuid4(),
        student_display_name="Grace Hopper",
        student_phone_number="+15550002222",
        microtopic_label="Physics: Kinematics",
        starts_at=datetime(2026, 1, 5, 21, 0, tzinfo=UTC),
    )
    return ExpiredRequest(**{**defaults, **overrides})


def test_subject_counts_and_pluralises_a_single_match() -> None:
    digest = notifications.build_digest([_match()], [], FRONTEND_ORIGIN)

    assert digest.subject == "Bridge AI: 1 new match"


def test_subject_counts_and_pluralises_multiple_matches_and_expirations() -> None:
    digest = notifications.build_digest([_match(), _match()], [_expiration()], FRONTEND_ORIGIN)

    assert digest.subject == "Bridge AI: 2 new matches, 1 expired request"


def test_an_expiration_only_digest_has_no_matches_section() -> None:
    expiration = _expiration()

    digest = notifications.build_digest([], [expiration], FRONTEND_ORIGIN)

    assert digest.subject == "Bridge AI: 1 expired request"
    assert "Grace Hopper" in digest.body
    assert "+15550002222" in digest.body
    assert "Physics: Kinematics" in digest.body
    assert "New matches" not in digest.body
