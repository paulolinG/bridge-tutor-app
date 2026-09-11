from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes import join as join_routes

SESSION_ID = uuid4()
JOIN_TOKEN = "abc123"

BASELINE_ITEMS = [
    {
        "concept": "Common denominators",
        "prompt": f"Question {index}",
        "options": ["a", "b", "c", "d"],
        "correct_index": 1,
    }
    for index in range(5)
]


def _live_session_row(status: str = "scheduled") -> dict:
    """A session currently in progress, so the join window is open."""
    now = datetime.now(UTC)
    return {
        "id": str(SESSION_ID),
        "tutor_id": str(uuid4()),
        "starts_at": (now - timedelta(minutes=10)).isoformat(),
        "ends_at": (now + timedelta(minutes=50)).isoformat(),
        "status": status,
        "daily_room_name": None,
        "whiteboard_snapshot": None,
        "session_requests": {"microtopics": {"label": "Math: Fractions"}},
    }


def _form(kind: str, **overrides) -> dict:
    return {
        "kind": kind,
        "items": BASELINE_ITEMS,
        "answers": None,
        "score_percent": None,
        "skipped": False,
        **overrides,
    }


def _patch(monkeypatch, row: dict, forms: list[dict]) -> None:
    async def fake_get_by_join_token(token) -> dict:
        return row

    async def fake_get_forms(session_id) -> list[dict]:
        return forms

    monkeypatch.setattr(join_routes.sessions_db, "get_by_join_token", fake_get_by_join_token)
    monkeypatch.setattr(join_routes.diagnostic_common.diagnostics_db, "get_forms", fake_get_forms)


def test_baseline_is_served_without_the_answer_key(monkeypatch, client: TestClient) -> None:
    _patch(monkeypatch, _live_session_row(), [_form("baseline"), _form("exit")])

    response = client.get(f"/join/{JOIN_TOKEN}/diagnostic")

    assert response.status_code == 200
    body = response.json()
    assert body["form"]["kind"] == "baseline"
    assert len(body["form"]["items"]) == 5
    assert "correct_index" not in response.text


def test_second_submission_is_refused(monkeypatch, client: TestClient) -> None:
    _patch(monkeypatch, _live_session_row(), [_form("baseline")])

    async def fake_submit_answers(session_id, kind, answers, score) -> bool:
        return False

    monkeypatch.setattr(
        join_routes.diagnostic_common.diagnostics_db, "submit_answers", fake_submit_answers
    )

    response = client.post(
        f"/join/{JOIN_TOKEN}/diagnostic/baseline", json={"answers": [1, 1, 1, 1, 1]}
    )

    assert response.status_code == 409


def test_submitting_scores_deterministically(monkeypatch, client: TestClient) -> None:
    _patch(monkeypatch, _live_session_row(), [_form("baseline")])
    recorded: dict = {}

    async def fake_submit_answers(session_id, kind, answers, score) -> bool:
        recorded["score"] = score
        return True

    monkeypatch.setattr(
        join_routes.diagnostic_common.diagnostics_db, "submit_answers", fake_submit_answers
    )

    # Every item's correct_index is 1; three of the five answers match.
    response = client.post(
        f"/join/{JOIN_TOKEN}/diagnostic/baseline", json={"answers": [1, 1, 1, 0, 0]}
    )

    assert response.status_code == 200
    assert recorded["score"] == 60.0


def test_a_skipped_baseline_is_never_offered_again(monkeypatch, client: TestClient) -> None:
    _patch(monkeypatch, _live_session_row(), [_form("baseline", skipped=True), _form("exit")])

    response = client.get(f"/join/{JOIN_TOKEN}/diagnostic")

    assert response.status_code == 200
    assert response.json()["form"] is None


def test_exit_ticket_is_offered_once_the_tutor_completes_the_session(
    monkeypatch, client: TestClient
) -> None:
    _patch(
        monkeypatch,
        _live_session_row(status="completed"),
        [_form("baseline", skipped=True), _form("exit")],
    )

    response = client.get(f"/join/{JOIN_TOKEN}/diagnostic")

    assert response.json()["form"]["kind"] == "exit"
