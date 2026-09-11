import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from app.db import sessions as sessions_db
from tests.test_matching_db import _FakeSupabaseClient

SESSION_ID = uuid4()
TUTOR_ID = uuid4()
JOIN_TOKEN = "abc123"


def test_get_by_join_token_filters_on_the_token_column(monkeypatch) -> None:
    row = {"id": str(SESSION_ID), "join_token": JOIN_TOKEN}
    fake = _FakeSupabaseClient([row])
    monkeypatch.setattr(sessions_db, "get_supabase", lambda: fake)

    result = asyncio.run(sessions_db.get_by_join_token(JOIN_TOKEN))

    assert result == row
    assert ("table", "sessions") in fake.calls
    assert ("eq", "join_token", JOIN_TOKEN) in fake.calls


def test_get_by_join_token_returns_none_when_not_found(monkeypatch) -> None:
    fake = _FakeSupabaseClient([])
    monkeypatch.setattr(sessions_db, "get_supabase", lambda: fake)

    result = asyncio.run(sessions_db.get_by_join_token("unknown"))

    assert result is None


def test_get_for_tutor_filters_on_id_and_tutor_id(monkeypatch) -> None:
    row = {"id": str(SESSION_ID), "tutor_id": str(TUTOR_ID)}
    fake = _FakeSupabaseClient([row])
    monkeypatch.setattr(sessions_db, "get_supabase", lambda: fake)

    result = asyncio.run(sessions_db.get_for_tutor(SESSION_ID, TUTOR_ID))

    assert result == row
    assert ("eq", "id", str(SESSION_ID)) in fake.calls
    assert ("eq", "tutor_id", str(TUTOR_ID)) in fake.calls


def test_get_for_tutor_returns_none_for_another_tutors_session(monkeypatch) -> None:
    fake = _FakeSupabaseClient([])
    monkeypatch.setattr(sessions_db, "get_supabase", lambda: fake)

    result = asyncio.run(sessions_db.get_for_tutor(SESSION_ID, TUTOR_ID))

    assert result is None


def test_set_daily_room_name_updates_by_id(monkeypatch) -> None:
    fake = _FakeSupabaseClient([{"id": str(SESSION_ID)}])
    monkeypatch.setattr(sessions_db, "get_supabase", lambda: fake)

    asyncio.run(sessions_db.set_daily_room_name(SESSION_ID, "bridge-abc"))

    assert ("update", {"daily_room_name": "bridge-abc"}) in fake.calls
    assert ("eq", "id", str(SESSION_ID)) in fake.calls


def test_set_status_compare_and_sets_on_scheduled(monkeypatch) -> None:
    fake = _FakeSupabaseClient([{"id": str(SESSION_ID)}])
    monkeypatch.setattr(sessions_db, "get_supabase", lambda: fake)
    completed_at = datetime(2026, 1, 5, 19, 0, tzinfo=UTC)

    updated = asyncio.run(sessions_db.set_status(SESSION_ID, TUTOR_ID, "completed", completed_at))

    assert updated is True
    assert ("update", {"status": "completed", "completed_at": completed_at.isoformat()}) in (
        fake.calls
    )
    assert ("eq", "id", str(SESSION_ID)) in fake.calls
    assert ("eq", "tutor_id", str(TUTOR_ID)) in fake.calls
    assert ("eq", "status", "scheduled") in fake.calls


def test_set_status_returns_false_when_already_terminal(monkeypatch) -> None:
    fake = _FakeSupabaseClient([])
    monkeypatch.setattr(sessions_db, "get_supabase", lambda: fake)

    updated = asyncio.run(sessions_db.set_status(SESSION_ID, TUTOR_ID, "no_show", None))

    assert updated is False


def test_set_whiteboard_snapshot_updates_by_id(monkeypatch) -> None:
    fake = _FakeSupabaseClient([{"id": str(SESSION_ID)}])
    monkeypatch.setattr(sessions_db, "get_supabase", lambda: fake)
    snapshot = {"document": {"shape:1": {"type": "rectangle"}}}

    asyncio.run(sessions_db.set_whiteboard_snapshot(SESSION_ID, snapshot))

    assert ("update", {"whiteboard_snapshot": snapshot}) in fake.calls
    assert ("eq", "id", str(SESSION_ID)) in fake.calls
