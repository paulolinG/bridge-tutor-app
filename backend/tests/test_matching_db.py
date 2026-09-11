import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from app.db import matching as matching_db

TUTOR_ID = uuid4()
REQUEST_ID = uuid4()
MICROTOPIC_ID = uuid4()


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


class _FakeTable:
    def __init__(self, calls: list[tuple], data: list[dict]) -> None:
        self._calls = calls
        self._data = data
        self.name: str | None = None

    def __call__(self, name: str) -> "_FakeTable":
        self.name = name
        self._calls.append(("table", name))
        return self

    def __getattr__(self, name: str) -> _RecordingBuilder:
        self._calls.append((name,))
        return _RecordingBuilder(self._calls, self._data)


class _FakeSupabaseClient:
    def __init__(self, data: list[dict]) -> None:
        self.calls: list[tuple] = []
        self._data = data

    def table(self, name: str) -> _RecordingBuilder:
        self.calls.append(("table", name))
        return _RecordingBuilder(self.calls, self._data)


def test_expire_stale_requests_filters_pending_before_cutoff(monkeypatch) -> None:
    fake = _FakeSupabaseClient([{"id": str(REQUEST_ID)}])
    monkeypatch.setattr(matching_db, "get_supabase", lambda: fake)

    now = datetime(2026, 1, 5, 18, 0, tzinfo=UTC)
    count = asyncio.run(matching_db.expire_stale_requests(now))

    assert count == 1
    assert ("table", "session_requests") in fake.calls
    assert ("update", {"status": "expired"}) in fake.calls
    assert ("eq", "status", "pending") in fake.calls
    assert ("lt", "starts_at", now.isoformat()) in fake.calls


def test_claim_request_returns_true_when_row_updated(monkeypatch) -> None:
    fake = _FakeSupabaseClient([{"id": str(REQUEST_ID)}])
    monkeypatch.setattr(matching_db, "get_supabase", lambda: fake)

    claimed = asyncio.run(matching_db.claim_request(REQUEST_ID))

    assert claimed is True
    assert ("update", {"status": "matched"}) in fake.calls
    assert ("eq", "id", str(REQUEST_ID)) in fake.calls
    assert ("eq", "status", "pending") in fake.calls


def test_claim_request_returns_false_when_already_claimed(monkeypatch) -> None:
    fake = _FakeSupabaseClient([])
    monkeypatch.setattr(matching_db, "get_supabase", lambda: fake)

    claimed = asyncio.run(matching_db.claim_request(REQUEST_ID))

    assert claimed is False


def test_list_availability_returns_empty_without_querying_for_no_tutors(monkeypatch) -> None:
    fake = _FakeSupabaseClient([{"tutor_id": str(TUTOR_ID)}])
    monkeypatch.setattr(matching_db, "get_supabase", lambda: fake)

    result = asyncio.run(matching_db.list_availability([]))

    assert result == []
    assert fake.calls == []


def test_list_scheduled_sessions_returns_empty_without_querying_for_no_tutors(monkeypatch) -> None:
    fake = _FakeSupabaseClient([{"tutor_id": str(TUTOR_ID)}])
    monkeypatch.setattr(matching_db, "get_supabase", lambda: fake)

    result = asyncio.run(
        matching_db.list_scheduled_sessions(
            [], datetime(2026, 1, 5, tzinfo=UTC), datetime(2026, 1, 12, tzinfo=UTC)
        )
    )

    assert result == []
    assert fake.calls == []


def test_list_certified_tutor_profiles_excludes_tutors_without_completed_onboarding(
    monkeypatch,
) -> None:
    fake = _FakeSupabaseClient(
        [
            {
                "tutor_id": str(TUTOR_ID),
                "tutor_profiles": {
                    "id": str(TUTOR_ID),
                    "daily_cap_minutes": 300,
                    "weekly_cap_minutes": 300,
                },
            },
            {
                "tutor_id": str(uuid4()),
                "tutor_profiles": {
                    "id": str(uuid4()),
                    "daily_cap_minutes": None,
                    "weekly_cap_minutes": None,
                },
            },
        ]
    )
    monkeypatch.setattr(matching_db, "get_supabase", lambda: fake)

    result = asyncio.run(matching_db.list_certified_tutor_profiles(MICROTOPIC_ID))

    assert len(result) == 1
    assert result[0]["tutor_id"] == str(TUTOR_ID)


def test_list_candidates_assembles_availability_and_commitments(monkeypatch) -> None:
    profile_rows = [
        {
            "tutor_id": str(TUTOR_ID),
            "tutor_profiles": {
                "id": str(TUTOR_ID),
                "daily_cap_minutes": 300,
                "weekly_cap_minutes": 300,
            },
        }
    ]

    async def _fake_certified(microtopic_id) -> list[dict]:
        return profile_rows

    async def _fake_availability(tutor_ids) -> list[dict]:
        assert tutor_ids == [TUTOR_ID]
        return [
            {"tutor_id": str(TUTOR_ID), "day_of_week": 0, "start_minute": 780, "end_minute": 840}
        ]

    async def _fake_sessions(tutor_ids, range_start, range_end) -> list[dict]:
        assert tutor_ids == [TUTOR_ID]
        return [
            {
                "tutor_id": str(TUTOR_ID),
                "starts_at": "2026-01-05T18:00:00+00:00",
                "ends_at": "2026-01-05T19:00:00+00:00",
            }
        ]

    monkeypatch.setattr(matching_db, "list_certified_tutor_profiles", _fake_certified)
    monkeypatch.setattr(matching_db, "list_availability", _fake_availability)
    monkeypatch.setattr(matching_db, "list_scheduled_sessions", _fake_sessions)

    candidates = asyncio.run(
        matching_db.list_candidates(
            MICROTOPIC_ID, datetime(2026, 1, 5, tzinfo=UTC), datetime(2026, 1, 12, tzinfo=UTC)
        )
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.tutor_id == TUTOR_ID
    assert candidate.daily_cap_minutes == 300
    assert len(candidate.availability) == 1
    assert candidate.availability[0].start_minute == 780
    assert len(candidate.commitments) == 1
    assert candidate.commitments[0].duration_minutes == 60


def test_create_session_returns_inserted_row(monkeypatch) -> None:
    inserted = {
        "id": str(uuid4()),
        "request_id": str(REQUEST_ID),
        "tutor_id": str(TUTOR_ID),
        "join_token": "abc123",
    }
    fake = _FakeSupabaseClient([inserted])
    monkeypatch.setattr(matching_db, "get_supabase", lambda: fake)

    result = asyncio.run(
        matching_db.create_session(
            REQUEST_ID,
            TUTOR_ID,
            datetime(2026, 1, 5, 18, 0, tzinfo=UTC),
            datetime(2026, 1, 5, 19, 0, tzinfo=UTC),
        )
    )

    assert result == inserted
    assert ("table", "sessions") in fake.calls
