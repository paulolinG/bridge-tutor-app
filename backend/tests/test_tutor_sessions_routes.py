from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import sessions as sessions_routes

TUTOR_ID = uuid4()
SESSION_ID = uuid4()


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


def test_post_call_returns_404_for_another_tutors_session(monkeypatch, client: TestClient) -> None:
    _authenticate_as(monkeypatch)

    async def fake_get_for_tutor(session_id, tutor_id) -> None:
        return None

    monkeypatch.setattr(sessions_routes.sessions_db, "get_for_tutor", fake_get_for_tutor)

    response = client.post(
        f"/tutors/me/sessions/{SESSION_ID}/call",
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 404


def test_post_message_returns_404_for_another_tutors_session(
    monkeypatch, client: TestClient
) -> None:
    _authenticate_as(monkeypatch)

    async def fake_get_for_tutor(session_id, tutor_id) -> None:
        return None

    monkeypatch.setattr(sessions_routes.sessions_db, "get_for_tutor", fake_get_for_tutor)

    response = client.post(
        f"/tutors/me/sessions/{SESSION_ID}/messages",
        json={"content": "hi"},
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == sessions_routes.SESSION_NOT_FOUND_DETAIL


def test_post_message_persists_with_sender_role_tutor(monkeypatch, client: TestClient) -> None:
    _authenticate_as(monkeypatch)

    async def fake_get_for_tutor(session_id, tutor_id) -> dict:
        return {
            "id": str(SESSION_ID),
            "starts_at": "2026-01-05T18:00:00+00:00",
            "ends_at": "2026-01-05T19:00:00+00:00",
            "status": "scheduled",
            "daily_room_name": None,
            "whiteboard_snapshot": None,
        }

    created_calls = []

    async def fake_create_message(session_id, sender_role, content) -> dict:
        created_calls.append((session_id, sender_role, content))
        return {
            "id": str(uuid4()),
            "sender_role": sender_role,
            "content": content,
            "created_at": "2026-01-05T18:00:00+00:00",
        }

    monkeypatch.setattr(sessions_routes.sessions_db, "get_for_tutor", fake_get_for_tutor)
    monkeypatch.setattr(
        sessions_routes.session_common.session_messages_db, "create_message", fake_create_message
    )
    monkeypatch.setattr(
        sessions_routes.session_common.sessions_service, "is_session_writable", lambda *a: True
    )

    response = client.post(
        f"/tutors/me/sessions/{SESSION_ID}/messages",
        json={"content": "hello student"},
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sender_role"] == "tutor"
    assert created_calls == [(SESSION_ID, "tutor", "hello student")]


def test_get_messages_returns_history_for_tutor(monkeypatch, client: TestClient) -> None:
    _authenticate_as(monkeypatch)

    async def fake_get_for_tutor(session_id, tutor_id) -> dict:
        return {
            "id": str(SESSION_ID),
            "starts_at": "2026-01-05T18:00:00+00:00",
            "ends_at": "2026-01-05T19:00:00+00:00",
            "status": "scheduled",
            "daily_room_name": None,
            "whiteboard_snapshot": None,
        }

    history = [
        {
            "id": str(uuid4()),
            "sender_role": "student",
            "content": "hi there",
            "created_at": "2026-01-05T18:00:00+00:00",
        }
    ]

    async def fake_list_messages(session_id) -> list[dict]:
        return history

    monkeypatch.setattr(sessions_routes.sessions_db, "get_for_tutor", fake_get_for_tutor)
    monkeypatch.setattr(
        sessions_routes.session_common.session_messages_db, "list_messages", fake_list_messages
    )

    response = client.get(
        f"/tutors/me/sessions/{SESSION_ID}/messages",
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 200
    assert response.json()[0]["content"] == "hi there"


def test_patch_status_returns_409_when_already_terminal(monkeypatch, client: TestClient) -> None:
    _authenticate_as(monkeypatch)

    async def fake_set_status(session_id, tutor_id, status, completed_at) -> bool:
        return False

    monkeypatch.setattr(sessions_routes.sessions_db, "set_status", fake_set_status)

    response = client.patch(
        f"/tutors/me/sessions/{SESSION_ID}",
        json={"status": "completed"},
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 409


def test_patch_status_succeeds_when_scheduled(monkeypatch, client: TestClient) -> None:
    _authenticate_as(monkeypatch)

    async def fake_set_status(session_id, tutor_id, status, completed_at) -> bool:
        assert status == "no_show"
        return True

    monkeypatch.setattr(sessions_routes.sessions_db, "set_status", fake_set_status)

    response = client.patch(
        f"/tutors/me/sessions/{SESSION_ID}",
        json={"status": "no_show"},
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "no_show"
