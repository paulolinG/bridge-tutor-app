import asyncio
from uuid import uuid4

from app.db import notifications as notifications_db

SESSION_ID = uuid4()
REQUEST_ID = uuid4()


class _FakeExecuteResult:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _RecordingBuilder:
    """Records every chained call and returns canned data from execute()."""

    def __init__(self, calls: list[tuple], data: list[dict]) -> None:
        self._calls = calls
        self._data = data

    def __getattr__(self, name: str):
        def _record(*args: object, **kwargs: object) -> "_RecordingBuilder":
            self._calls.append((name, *args))
            return self

        return _record

    def execute(self) -> _FakeExecuteResult:
        self._calls.append(("execute",))
        return _FakeExecuteResult(self._data)


class _FakeSupabaseClient:
    def __init__(self, data: list[dict]) -> None:
        self.calls: list[tuple] = []
        self._data = data

    def table(self, name: str) -> _RecordingBuilder:
        self.calls.append(("table", name))
        return _RecordingBuilder(self.calls, self._data)


def test_list_unnotified_matches_filters_on_coordinator_notified_at(monkeypatch) -> None:
    fake = _FakeSupabaseClient([{"id": str(SESSION_ID)}])
    monkeypatch.setattr(notifications_db, "get_supabase", lambda: fake)

    rows = asyncio.run(notifications_db.list_unnotified_matches())

    assert rows == [{"id": str(SESSION_ID)}]
    assert ("table", "sessions") in fake.calls
    assert ("is_", "coordinator_notified_at", "null") in fake.calls


def test_mark_notified_stamps_both_tables(monkeypatch) -> None:
    fake = _FakeSupabaseClient([])
    monkeypatch.setattr(notifications_db, "get_supabase", lambda: fake)

    asyncio.run(notifications_db.mark_notified([SESSION_ID], [REQUEST_ID]))

    assert ("table", "sessions") in fake.calls
    assert ("table", "session_requests") in fake.calls
    assert ("in_", "id", [str(SESSION_ID)]) in fake.calls
    assert ("in_", "id", [str(REQUEST_ID)]) in fake.calls
