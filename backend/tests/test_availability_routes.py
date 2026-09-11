from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import availability as availability_routes

TUTOR_ID = uuid4()


class _FakeAuthUser:
    def __init__(self, user_id: str) -> None:
        self.id = user_id
        self.email = "ada@example.com"


class _FakeAuthResponse:
    def __init__(self, user: object | None) -> None:
        self.user = user


class _FakeAuth:
    def __init__(self, user: object | None) -> None:
        self._user = user

    def get_user(self, token: str) -> _FakeAuthResponse:
        return _FakeAuthResponse(self._user)


class _FakeSupabaseClient:
    def __init__(self, user: object | None) -> None:
        self.auth = _FakeAuth(user)


def _authenticate_as(monkeypatch, tutor_id: str = str(TUTOR_ID)) -> None:
    monkeypatch.setattr(deps, "get_supabase", lambda: _FakeSupabaseClient(_FakeAuthUser(tutor_id)))


def test_get_availability_requires_auth(client: TestClient) -> None:
    response = client.get("/tutors/me/availability")
    assert response.status_code == 401


def test_put_availability_rejects_window_with_start_after_end(
    monkeypatch, client: TestClient
) -> None:
    _authenticate_as(monkeypatch)

    response = client.put(
        "/tutors/me/availability",
        json={
            "windows": [{"day_of_week": 0, "start_minute": 600, "end_minute": 500}],
            "daily_cap_minutes": 120,
            "weekly_cap_minutes": 600,
        },
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 422


def test_put_availability_replaces_windows_and_caps(monkeypatch, client: TestClient) -> None:
    _authenticate_as(monkeypatch)

    calls = {}

    async def fake_replace(tutor_id, windows) -> None:
        calls["windows"] = windows

    async def fake_update_capacity(tutor_id, daily_cap_minutes, weekly_cap_minutes) -> dict:
        calls["caps"] = (daily_cap_minutes, weekly_cap_minutes)
        return {}

    monkeypatch.setattr(
        availability_routes.availability_db, "replace_availability_windows", fake_replace
    )
    monkeypatch.setattr(
        availability_routes.availability_db, "update_capacity", fake_update_capacity
    )

    response = client.put(
        "/tutors/me/availability",
        json={
            "windows": [{"day_of_week": 0, "start_minute": 780, "end_minute": 840}],
            "daily_cap_minutes": 120,
            "weekly_cap_minutes": 600,
        },
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["daily_cap_minutes"] == 120
    assert body["weekly_cap_minutes"] == 600
    assert len(body["windows"]) == 1
    assert calls["caps"] == (120, 600)
