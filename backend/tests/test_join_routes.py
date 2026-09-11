from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes import join as join_routes

SESSION_ID = uuid4()
JOIN_TOKEN = "abc123"


def _session_row(status: str = "scheduled", daily_room_name: str | None = None) -> dict:
    return {
        "id": str(SESSION_ID),
        "tutor_id": str(uuid4()),
        "starts_at": "2026-01-05T18:00:00+00:00",
        "ends_at": "2026-01-05T19:00:00+00:00",
        "status": status,
        "daily_room_name": daily_room_name,
        "whiteboard_snapshot": None,
        "session_requests": {"microtopics": {"label": "Physics: Kinematics"}},
    }


def test_get_join_info_returns_404_for_unknown_token(monkeypatch, client: TestClient) -> None:
    async def fake_get_by_join_token(token) -> None:
        return None

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)

    response = client.get(f"/join/{JOIN_TOKEN}")

    assert response.status_code == 404


def test_get_join_info_returns_200_with_join_closed_outside_window(
    monkeypatch, client: TestClient
) -> None:
    async def fake_get_by_join_token(token) -> dict:
        return _session_row()

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)

    response = client.get(f"/join/{JOIN_TOKEN}")

    assert response.status_code == 200
    body = response.json()
    assert body["join_open"] is False
    assert body["microtopic_label"] == "Physics: Kinematics"


def test_post_call_returns_403_outside_join_window(monkeypatch, client: TestClient) -> None:
    async def fake_get_by_join_token(token) -> dict:
        return _session_row()

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)

    response = client.post(f"/join/{JOIN_TOKEN}/call")

    assert response.status_code == 403


def test_post_call_mints_a_token_and_persists_the_room_on_first_join(
    monkeypatch, client: TestClient
) -> None:
    async def fake_get_by_join_token(token) -> dict:
        return _session_row()

    async def fake_create_room(name, exp) -> str:
        return name

    async def fake_create_meeting_token(room_name, user_name, is_owner, exp) -> str:
        assert is_owner is False
        return "student-jwt"

    set_room_calls = []

    async def fake_set_daily_room_name(session_id, room_name) -> None:
        set_room_calls.append((session_id, room_name))

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)
    monkeypatch.setattr(join_routes.sessions_db, "set_daily_room_name", fake_set_daily_room_name)
    monkeypatch.setattr(join_routes.daily, "create_room", fake_create_room)
    monkeypatch.setattr(join_routes.daily, "create_meeting_token", fake_create_meeting_token)
    monkeypatch.setattr(join_routes.sessions_service, "is_join_open", lambda *a: True)

    response = client.post(f"/join/{JOIN_TOKEN}/call")

    assert response.status_code == 200
    body = response.json()
    assert body["token"] == "student-jwt"
    assert len(set_room_calls) == 1
    assert set_room_calls[0][0] == SESSION_ID


def test_post_call_reuses_an_existing_room(monkeypatch, client: TestClient) -> None:
    async def fake_get_by_join_token(token) -> dict:
        return _session_row(daily_room_name="bridge-existing")

    async def fake_create_meeting_token(room_name, user_name, is_owner, exp) -> str:
        assert room_name == "bridge-existing"
        return "student-jwt"

    def fail_create_room(*args, **kwargs) -> None:
        raise AssertionError("create_room should not be called when a room already exists")

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)
    monkeypatch.setattr(join_routes.daily, "create_room", fail_create_room)
    monkeypatch.setattr(join_routes.daily, "create_meeting_token", fake_create_meeting_token)
    monkeypatch.setattr(join_routes.sessions_service, "is_join_open", lambda *a: True)

    response = client.post(f"/join/{JOIN_TOKEN}/call")

    assert response.status_code == 200


def test_post_message_returns_404_for_unknown_token(monkeypatch, client: TestClient) -> None:
    async def fake_get_by_join_token(token) -> None:
        return None

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)

    response = client.post(f"/join/{JOIN_TOKEN}/messages", json={"content": "hi"})

    assert response.status_code == 404
    assert response.json()["detail"] == join_routes.SESSION_NOT_FOUND_DETAIL


def test_post_message_returns_403_when_session_has_ended(monkeypatch, client: TestClient) -> None:
    async def fake_get_by_join_token(token) -> dict:
        return _session_row(status="completed")

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)

    response = client.post(f"/join/{JOIN_TOKEN}/messages", json={"content": "hi"})

    assert response.status_code == 403


def test_post_message_persists_with_sender_role_student(monkeypatch, client: TestClient) -> None:
    async def fake_get_by_join_token(token) -> dict:
        return _session_row()

    created_calls = []

    async def fake_create_message(session_id, sender_role, content) -> dict:
        created_calls.append((session_id, sender_role, content))
        return {
            "id": str(uuid4()),
            "sender_role": sender_role,
            "content": content,
            "created_at": "2026-01-05T18:00:00+00:00",
        }

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)
    monkeypatch.setattr(
        join_routes.session_common.session_messages_db, "create_message", fake_create_message
    )
    monkeypatch.setattr(
        join_routes.session_common.sessions_service, "is_session_writable", lambda *a: True
    )

    response = client.post(f"/join/{JOIN_TOKEN}/messages", json={"content": "hello there"})

    assert response.status_code == 200
    body = response.json()
    assert body["sender_role"] == "student"
    assert body["content"] == "hello there"
    assert created_calls == [(SESSION_ID, "student", "hello there")]


def test_get_messages_returns_history(monkeypatch, client: TestClient) -> None:
    async def fake_get_by_join_token(token) -> dict:
        return _session_row()

    history = [
        {
            "id": str(uuid4()),
            "sender_role": "tutor",
            "content": "welcome",
            "created_at": "2026-01-05T18:00:00+00:00",
        },
        {
            "id": str(uuid4()),
            "sender_role": "student",
            "content": "thanks",
            "created_at": "2026-01-05T18:01:00+00:00",
        },
    ]

    async def fake_list_messages(session_id) -> list[dict]:
        assert session_id == SESSION_ID
        return history

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)
    monkeypatch.setattr(
        join_routes.session_common.session_messages_db, "list_messages", fake_list_messages
    )

    response = client.get(f"/join/{JOIN_TOKEN}/messages")

    assert response.status_code == 200
    body = response.json()
    assert [m["content"] for m in body] == ["welcome", "thanks"]


def test_put_then_get_whiteboard_round_trips_the_snapshot(monkeypatch, client: TestClient) -> None:
    snapshot = {"document": {"shape:1": {"type": "rectangle"}}}
    stored = {}

    async def fake_get_by_join_token(token) -> dict:
        row = _session_row()
        row["whiteboard_snapshot"] = stored.get("snapshot")
        return row

    async def fake_set_whiteboard_snapshot(session_id, new_snapshot) -> None:
        assert session_id == SESSION_ID
        stored["snapshot"] = new_snapshot

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)
    monkeypatch.setattr(
        join_routes.session_common.sessions_db,
        "set_whiteboard_snapshot",
        fake_set_whiteboard_snapshot,
    )
    monkeypatch.setattr(
        join_routes.session_common.sessions_service, "is_session_writable", lambda *a: True
    )

    put_response = client.put(f"/join/{JOIN_TOKEN}/whiteboard", json={"snapshot": snapshot})
    assert put_response.status_code == 200

    get_response = client.get(f"/join/{JOIN_TOKEN}/whiteboard")
    assert get_response.status_code == 200
    assert get_response.json()["snapshot"] == snapshot
