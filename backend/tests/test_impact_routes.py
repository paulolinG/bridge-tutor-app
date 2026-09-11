from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import impact as impact_routes

TUTOR_ID = uuid4()
STUDENT_ID = uuid4()


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


def _row(status: str, forms: list[dict]) -> dict:
    return {
        "id": str(uuid4()),
        "status": status,
        "session_requests": {
            "student_id": str(STUDENT_ID),
            "duration_minutes": 60,
            "microtopics": {"label": "Math: Fractions"},
        },
        "session_diagnostic_forms": forms,
    }


def test_impact_reports_the_measured_denominator(monkeypatch, client: TestClient) -> None:
    _authenticate_as(monkeypatch)

    async def fake_list_tutor_sessions(tutor_id) -> list[dict]:
        return [
            _row(
                "completed",
                [
                    {"kind": "baseline", "score_percent": 40.0},
                    {"kind": "exit", "score_percent": 80.0},
                ],
            ),
            _row(
                "completed",
                [
                    {"kind": "baseline", "score_percent": None},
                    {"kind": "exit", "score_percent": 80.0},
                ],
            ),
            _row("cancelled", []),
        ]

    monkeypatch.setattr(impact_routes.impact_db, "list_tutor_sessions", fake_list_tutor_sessions)

    response = client.get("/tutors/me/impact", headers={"Authorization": "Bearer good-token"})

    assert response.status_code == 200
    body = response.json()
    assert body["sessions_completed"] == 2
    assert body["volunteer_minutes"] == 120
    assert body["students_helped"] == 1

    entry = body["by_microtopic"][0]
    assert entry["average_delta_growth"] == 40.0
    assert entry["measured_sessions"] == 1
    assert entry["total_sessions"] == 2
