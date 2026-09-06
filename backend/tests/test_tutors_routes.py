from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import tutors as tutors_routes

TUTOR_ID = uuid4()
TUTOR_EMAIL = "ada@example.com"


class _FakeAuthUser:
    def __init__(self, user_id: str, email: str) -> None:
        self.id = user_id
        self.email = email


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


class _RaisingAuth:
    def get_user(self, token: str) -> None:
        from supabase_auth.errors import AuthApiError

        raise AuthApiError("invalid JWT: unable to parse or verify signature", 401, "bad_jwt")


class _RaisingSupabaseClient:
    def __init__(self) -> None:
        self.auth = _RaisingAuth()


def _authenticate_as(
    monkeypatch, tutor_id: str = str(TUTOR_ID), email: str | None = TUTOR_EMAIL
) -> None:
    monkeypatch.setattr(
        deps, "get_supabase", lambda: _FakeSupabaseClient(_FakeAuthUser(tutor_id, email))
    )


def test_create_profile_requires_auth_header(client: TestClient) -> None:
    response = client.post("/tutors", json={"display_name": "Ada"})

    assert response.status_code == 401


def test_create_profile_rejects_invalid_token(monkeypatch, client: TestClient) -> None:
    monkeypatch.setattr(deps, "get_supabase", lambda: _FakeSupabaseClient(user=None))

    response = client.post(
        "/tutors",
        json={"display_name": "Ada"},
        headers={"Authorization": "Bearer bad-token"},
    )

    assert response.status_code == 401


def test_create_profile_rejects_malformed_token(monkeypatch, client: TestClient) -> None:
    monkeypatch.setattr(deps, "get_supabase", lambda: _RaisingSupabaseClient())

    response = client.post(
        "/tutors",
        json={"display_name": "Ada"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


def test_create_profile_rejects_account_with_no_email(monkeypatch, client: TestClient) -> None:
    _authenticate_as(monkeypatch, email=None)

    async def fake_get_tutor_profile(tutor_id) -> None:
        return None

    async def fake_create_tutor_profile(tutor_id, email: str, display_name: str) -> dict:
        raise AssertionError("create_tutor_profile should not be called without an email")

    monkeypatch.setattr(tutors_routes.tutors_db, "get_tutor_profile", fake_get_tutor_profile)
    monkeypatch.setattr(tutors_routes.tutors_db, "create_tutor_profile", fake_create_tutor_profile)

    response = client.post(
        "/tutors",
        json={"display_name": "Ada"},
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 400


def test_create_profile_creates_new_profile(monkeypatch, client: TestClient) -> None:
    _authenticate_as(monkeypatch)

    async def fake_get_tutor_profile(tutor_id) -> None:
        return None

    monkeypatch.setattr(tutors_routes.tutors_db, "get_tutor_profile", fake_get_tutor_profile)

    calls: dict[str, object] = {}

    async def fake_create_tutor_profile(tutor_id, email: str, display_name: str) -> dict:
        calls["tutor_id"] = tutor_id
        calls["email"] = email
        calls["display_name"] = display_name
        return {
            "id": str(TUTOR_ID),
            "email": email,
            "display_name": display_name,
            "certification_status": "not_started",
        }

    monkeypatch.setattr(tutors_routes.tutors_db, "create_tutor_profile", fake_create_tutor_profile)

    response = client.post(
        "/tutors",
        json={"display_name": "Ada"},
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(TUTOR_ID)
    assert body["email"] == TUTOR_EMAIL
    assert body["display_name"] == "Ada"
    assert body["certification_status"] == "not_started"
    # email comes from the verified JWT, never from client-supplied request data
    assert calls["email"] == TUTOR_EMAIL


def test_create_profile_returns_existing_profile_without_recreating(
    monkeypatch, client: TestClient
) -> None:
    _authenticate_as(monkeypatch)

    existing_row = {
        "id": str(TUTOR_ID),
        "email": TUTOR_EMAIL,
        "display_name": "Ada Lovelace",
        "certification_status": "passed",
    }

    async def fake_get_tutor_profile(tutor_id) -> dict:
        return existing_row

    async def fake_create_tutor_profile(tutor_id, email: str, display_name: str) -> dict:
        raise AssertionError("create_tutor_profile should not be called when a profile exists")

    monkeypatch.setattr(tutors_routes.tutors_db, "get_tutor_profile", fake_get_tutor_profile)
    monkeypatch.setattr(tutors_routes.tutors_db, "create_tutor_profile", fake_create_tutor_profile)

    response = client.post(
        "/tutors",
        json={"display_name": "A different name"},
        headers={"Authorization": "Bearer good-token"},
    )

    assert response.status_code == 200
    assert response.json() == existing_row
