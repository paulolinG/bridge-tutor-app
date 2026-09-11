import asyncio
from uuid import uuid4

from app.db import diagnostics as diagnostics_db

SESSION_ID = uuid4()


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


def test_create_pair_inserts_both_kinds_for_the_session(monkeypatch) -> None:
    fake = _FakeSupabaseClient([{"id": str(uuid4())}, {"id": str(uuid4())}])
    monkeypatch.setattr(diagnostics_db, "get_supabase", lambda: fake)

    asyncio.run(
        diagnostics_db.create_pair(
            SESSION_ID,
            baseline_items=[{"prompt": "a"}],
            exit_items=[{"prompt": "b"}],
        )
    )

    inserted = next(args for name, *args in fake.calls if name == "insert")[0]
    assert [row["kind"] for row in inserted] == ["baseline", "exit"]
    assert all(row["session_id"] == str(SESSION_ID) for row in inserted)


def test_submit_answers_refuses_a_second_submission(monkeypatch) -> None:
    # The conditional update matches no row when answers are already present.
    fake = _FakeSupabaseClient([])
    monkeypatch.setattr(diagnostics_db, "get_supabase", lambda: fake)

    wrote = asyncio.run(
        diagnostics_db.submit_answers(SESSION_ID, "baseline", [0, 1, 2, 3, 0], 60.0)
    )

    assert wrote is False
    assert ("is_", "answers", "null") in fake.calls
