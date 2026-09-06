import asyncio
from uuid import uuid4

from app.db import tutors as tutors_db

TUTOR_ID = uuid4()
TUTOR_EMAIL = "ada@example.com"


class _FakeExecuteResult:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _DuplicateKeyError(Exception):
    code = "23505"


class _FakeInsertBuilder:
    def execute(self) -> None:
        raise _DuplicateKeyError("duplicate key value violates unique constraint")


class _FakeEqBuilder:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def execute(self) -> _FakeExecuteResult:
        return _FakeExecuteResult([self._row] if self._row else [])


class _FakeSelectBuilder:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def eq(self, column: str, value: str) -> _FakeEqBuilder:
        return _FakeEqBuilder(self._row)


class _FakeTable:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def insert(self, payload: dict) -> _FakeInsertBuilder:
        return _FakeInsertBuilder()

    def select(self, columns: str) -> _FakeSelectBuilder:
        return _FakeSelectBuilder(self._row)


class _FakeSupabaseClient:
    def __init__(self, row: dict | None) -> None:
        self._row = row

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self._row)


def test_create_tutor_profile_returns_existing_row_on_concurrent_conflict(monkeypatch) -> None:
    existing_row = {
        "id": str(TUTOR_ID),
        "email": TUTOR_EMAIL,
        "display_name": "Ada",
        "certification_status": "not_started",
    }
    monkeypatch.setattr(tutors_db, "get_supabase", lambda: _FakeSupabaseClient(existing_row))
    # Make the module's duplicate-key detection recognize our fake exception type.
    monkeypatch.setattr(tutors_db, "APIError", _DuplicateKeyError)

    result = asyncio.run(tutors_db.create_tutor_profile(TUTOR_ID, TUTOR_EMAIL, "A different name"))

    assert result == existing_row
