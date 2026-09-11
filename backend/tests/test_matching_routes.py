from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import matching as matching_routes
from app.core.config import get_settings
from app.models.diagnostic import ConceptBlueprint, ConceptSlot, DiagnosticItem, DiagnosticPair


@pytest.fixture(autouse=True)
def _no_diagnostics_to_generate(monkeypatch):
    """Keeps these tests about matching. Generation has its own tests below."""

    async def fake_list(now, limit) -> list[dict]:
        return []

    monkeypatch.setattr(matching_routes.diagnostics_db, "list_session_ids_missing_forms", fake_list)


@pytest.fixture(autouse=True)
def _nothing_to_notify(monkeypatch):
    """Keeps these tests about matching. Notification has its own tests below."""

    async def fake_matches() -> list[dict]:
        return []

    async def fake_expirations() -> list[dict]:
        return []

    monkeypatch.setattr(matching_routes.notifications_db, "list_unnotified_matches", fake_matches)
    monkeypatch.setattr(
        matching_routes.notifications_db, "list_unnotified_expirations", fake_expirations
    )


MICROTOPIC_ID = uuid4()
STUDENT_ID = uuid4()
TUTOR_ID = uuid4()


def _pending_request_row(
    request_id=None,
    starts_at: str = "2026-01-05T18:00:00+00:00",
    created_at: str = "2026-01-01T00:00:00+00:00",
) -> dict:
    return {
        "id": str(request_id or uuid4()),
        "student_id": str(STUDENT_ID),
        "microtopic_id": str(MICROTOPIC_ID),
        "starts_at": starts_at,
        "duration_minutes": 60,
        "created_at": created_at,
        "student_profiles": {"academic_average": None, "regions": None},
    }


def _set_secret(monkeypatch, secret: str = "test-secret") -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("MATCHING_SECRET", secret)
    monkeypatch.setattr(matching_routes, "get_settings", get_settings)


def test_run_requires_secret_header(monkeypatch, client: TestClient) -> None:
    _set_secret(monkeypatch)

    response = client.post("/internal/matching/run")

    assert response.status_code == 401


def test_run_rejects_wrong_secret(monkeypatch, client: TestClient) -> None:
    _set_secret(monkeypatch)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "wrong-secret"})

    assert response.status_code == 401


def test_run_returns_503_when_secret_not_configured(monkeypatch, client: TestClient) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("MATCHING_SECRET", "")
    monkeypatch.setattr(matching_routes, "get_settings", get_settings)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "anything"})

    assert response.status_code == 503


def test_run_expires_stale_requests_and_reports_counts(monkeypatch, client: TestClient) -> None:
    _set_secret(monkeypatch)

    async def fake_expire(now) -> int:
        return 2

    async def fake_list_pending() -> list[dict]:
        return []

    monkeypatch.setattr(matching_routes.matching_db, "expire_stale_requests", fake_expire)
    monkeypatch.setattr(matching_routes.matching_db, "list_pending_requests", fake_list_pending)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json() == {
        "expired": 2,
        "processed": 0,
        "matched": 0,
        "diagnostics_generated": 0,
        "notified": 0,
    }


def test_run_matches_a_pending_request_when_domain_is_non_empty(
    monkeypatch, client: TestClient
) -> None:
    _set_secret(monkeypatch)
    row = _pending_request_row()

    async def fake_expire(now) -> int:
        return 0

    async def fake_list_pending() -> list[dict]:
        return [row]

    async def fake_list_candidates(microtopic_id, range_start, range_end):
        from app.models.matching import AvailabilityWindow, TutorCandidate

        return [
            TutorCandidate(
                tutor_id=TUTOR_ID,
                daily_cap_minutes=300,
                weekly_cap_minutes=300,
                availability=(
                    AvailabilityWindow(day_of_week=0, start_minute=13 * 60, end_minute=14 * 60),
                ),
                commitments=(),
            )
        ]

    claimed_ids = []

    async def fake_claim(request_id) -> bool:
        claimed_ids.append(request_id)
        return True

    created_sessions = []

    async def fake_create_session(request_id, tutor_id, starts_at, ends_at) -> dict:
        created_sessions.append((request_id, tutor_id, starts_at, ends_at))
        return {"id": str(uuid4()), "join_token": "tok"}

    monkeypatch.setattr(matching_routes.matching_db, "expire_stale_requests", fake_expire)
    monkeypatch.setattr(matching_routes.matching_db, "list_pending_requests", fake_list_pending)
    monkeypatch.setattr(matching_routes.matching_db, "list_candidates", fake_list_candidates)
    monkeypatch.setattr(matching_routes.matching_db, "claim_request", fake_claim)
    monkeypatch.setattr(matching_routes.matching_db, "create_session", fake_create_session)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json() == {
        "expired": 0,
        "processed": 1,
        "matched": 1,
        "diagnostics_generated": 0,
        "notified": 0,
    }
    assert len(claimed_ids) == 1
    assert len(created_sessions) == 1
    assert created_sessions[0][1] == TUTOR_ID


def test_run_leaves_request_pending_when_domain_is_empty(monkeypatch, client: TestClient) -> None:
    _set_secret(monkeypatch)
    row = _pending_request_row()

    async def fake_expire(now) -> int:
        return 0

    async def fake_list_pending() -> list[dict]:
        return [row]

    async def fake_list_candidates(microtopic_id, range_start, range_end):
        return []

    async def fake_claim(request_id) -> bool:
        raise AssertionError("claim_request should not be called for an empty domain")

    monkeypatch.setattr(matching_routes.matching_db, "expire_stale_requests", fake_expire)
    monkeypatch.setattr(matching_routes.matching_db, "list_pending_requests", fake_list_pending)
    monkeypatch.setattr(matching_routes.matching_db, "list_candidates", fake_list_candidates)
    monkeypatch.setattr(matching_routes.matching_db, "claim_request", fake_claim)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json() == {
        "expired": 0,
        "processed": 1,
        "matched": 0,
        "diagnostics_generated": 0,
        "notified": 0,
    }


def test_run_accounts_for_in_batch_matches_when_evaluating_later_requests(
    monkeypatch, client: TestClient
) -> None:
    """Two requests for the same Monday 13:00-14:00 slot, one tutor with a
    60-minute daily cap. The first request should consume the tutor's entire
    cap, so the second request (created later, thus lower urgency-tie
    priority) must find an empty domain despite the tutor being in the raw
    candidate list both times."""
    _set_secret(monkeypatch)
    first_row = _pending_request_row(created_at="2026-01-01T00:00:00+00:00")
    second_row = _pending_request_row(created_at="2026-01-02T00:00:00+00:00")

    async def fake_expire(now) -> int:
        return 0

    async def fake_list_pending() -> list[dict]:
        return [second_row, first_row]

    async def fake_list_candidates(microtopic_id, range_start, range_end):
        from app.models.matching import AvailabilityWindow, TutorCandidate

        return [
            TutorCandidate(
                tutor_id=TUTOR_ID,
                daily_cap_minutes=60,
                weekly_cap_minutes=300,
                availability=(
                    AvailabilityWindow(day_of_week=0, start_minute=13 * 60, end_minute=14 * 60),
                ),
                commitments=(),
            )
        ]

    async def fake_claim(request_id) -> bool:
        return True

    async def fake_create_session(request_id, tutor_id, starts_at, ends_at) -> dict:
        return {"id": str(uuid4()), "join_token": "tok"}

    monkeypatch.setattr(matching_routes.matching_db, "expire_stale_requests", fake_expire)
    monkeypatch.setattr(matching_routes.matching_db, "list_pending_requests", fake_list_pending)
    monkeypatch.setattr(matching_routes.matching_db, "list_candidates", fake_list_candidates)
    monkeypatch.setattr(matching_routes.matching_db, "claim_request", fake_claim)
    monkeypatch.setattr(matching_routes.matching_db, "create_session", fake_create_session)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json() == {
        "expired": 0,
        "processed": 2,
        "matched": 1,
        "diagnostics_generated": 0,
        "notified": 0,
    }


def _missing_row(concepts=None) -> dict:
    return {
        "id": str(uuid4()),
        "session_requests": {
            "microtopic_id": str(MICROTOPIC_ID),
            "microtopics": {"label": "Math: Fractions", "concepts": concepts},
            "student_profiles": {"grade_level": "Grade 8"},
        },
    }


def _patch_no_matching(monkeypatch) -> None:
    """Stubs out matching itself so these tests are only about generation."""

    async def fake_expire(now) -> int:
        return 0

    async def fake_list_pending() -> list[dict]:
        return []

    monkeypatch.setattr(matching_routes.matching_db, "expire_stale_requests", fake_expire)
    monkeypatch.setattr(matching_routes.matching_db, "list_pending_requests", fake_list_pending)


def _patch_missing(monkeypatch, rows: list[dict]) -> None:
    async def fake_list(now, limit) -> list[dict]:
        return rows

    monkeypatch.setattr(matching_routes.diagnostics_db, "list_session_ids_missing_forms", fake_list)


def _real_pair() -> DiagnosticPair:
    """A structurally valid pair, so items_for() is exercised for real."""
    return DiagnosticPair(
        slots=[
            ConceptSlot(
                concept=f"Concept {index}",
                baseline=DiagnosticItem(
                    prompt=f"Baseline {index}", options=["a", "b", "c", "d"], correct_index=0
                ),
                exit=DiagnosticItem(
                    prompt=f"Exit {index}", options=["a", "b", "c", "d"], correct_index=1
                ),
            )
            for index in range(5)
        ]
    )


def test_run_generates_diagnostics_for_sessions_missing_them(
    monkeypatch, client: TestClient
) -> None:
    _set_secret(monkeypatch)
    _patch_no_matching(monkeypatch)
    _patch_missing(monkeypatch, [_missing_row(concepts=["a", "b", "c", "d", "e"])])

    created: dict = {}

    async def fake_generate_pair(label, concepts, grade_level):
        created["grade_level"] = grade_level
        created["concepts"] = concepts
        return _real_pair()

    async def fake_create_pair(session_id, baseline_items, exit_items) -> None:
        created["baseline"] = baseline_items
        created["exit"] = exit_items

    monkeypatch.setattr(matching_routes, "generate_pair", fake_generate_pair)
    monkeypatch.setattr(matching_routes.diagnostics_db, "create_pair", fake_create_pair)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "test-secret"})

    assert response.json()["diagnostics_generated"] == 1
    assert created["grade_level"] == "Grade 8"
    assert [item["prompt"] for item in created["baseline"]] == [f"Baseline {i}" for i in range(5)]
    assert [item["prompt"] for item in created["exit"]] == [f"Exit {i}" for i in range(5)]
    # Both sides cover the same concepts, in the same order - the invariant
    # the slot-shaped schema exists to guarantee.
    assert [item["concept"] for item in created["baseline"]] == [
        item["concept"] for item in created["exit"]
    ]


def test_a_failed_generation_never_fails_the_run(monkeypatch, client: TestClient) -> None:
    _set_secret(monkeypatch)
    _patch_no_matching(monkeypatch)
    _patch_missing(monkeypatch, [_missing_row(concepts=["a", "b", "c", "d", "e"])])

    async def exploding_generate_pair(label, concepts, grade_level):
        raise RuntimeError("Anthropic is down")

    monkeypatch.setattr(matching_routes, "generate_pair", exploding_generate_pair)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json()["diagnostics_generated"] == 0


def test_a_microtopic_without_a_blueprint_gets_one_backfilled(
    monkeypatch, client: TestClient
) -> None:
    _set_secret(monkeypatch)
    _patch_no_matching(monkeypatch)
    _patch_missing(monkeypatch, [_missing_row(concepts=None)])

    backfilled: dict = {}

    async def fake_generate_blueprint(label, grade_level):
        return ConceptBlueprint(concepts=["one", "two", "three", "four", "five"])

    async def fake_set_concepts(microtopic_id, concepts) -> None:
        backfilled["concepts"] = concepts

    async def fake_generate_pair(label, concepts, grade_level):
        backfilled["used"] = concepts
        return _real_pair()

    async def fake_create_pair(session_id, baseline_items, exit_items) -> None:
        return None

    monkeypatch.setattr(matching_routes, "generate_blueprint", fake_generate_blueprint)
    monkeypatch.setattr(matching_routes, "generate_pair", fake_generate_pair)
    monkeypatch.setattr(
        matching_routes.diagnostics_db, "set_microtopic_concepts", fake_set_concepts
    )
    monkeypatch.setattr(matching_routes.diagnostics_db, "create_pair", fake_create_pair)

    client.post("/internal/matching/run", headers={"X-Matching-Secret": "test-secret"})

    assert backfilled["concepts"] == ["one", "two", "three", "four", "five"]
    assert backfilled["used"] == backfilled["concepts"]


def _matched_session_row(**overrides) -> dict:
    defaults = dict(
        id=str(uuid4()),
        join_token="tok123",
        starts_at="2026-01-05T21:00:00+00:00",
        session_requests={
            "microtopics": {"label": "Math: Fractions"},
            "student_profiles": {"display_name": "Ada Lovelace", "phone_number": "+15550001111"},
        },
    )
    return {**defaults, **overrides}


def _expired_request_row(**overrides) -> dict:
    defaults = dict(
        id=str(uuid4()),
        starts_at="2026-01-05T21:00:00+00:00",
        microtopics={"label": "Physics: Kinematics"},
        student_profiles={"display_name": "Grace Hopper", "phone_number": "+15550002222"},
    )
    return {**defaults, **overrides}


def _set_email_config(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("RESEND_API_KEY", "test-resend-key")
    monkeypatch.setenv("COORDINATOR_EMAIL", "coordinator@example.com")
    monkeypatch.setattr(matching_routes, "get_settings", get_settings)


def test_a_successful_digest_stamps_everything_it_covered(monkeypatch, client: TestClient) -> None:
    _set_secret(monkeypatch)
    _set_email_config(monkeypatch)
    _patch_no_matching(monkeypatch)
    match_row = _matched_session_row()
    expiration_row = _expired_request_row()

    async def fake_matches() -> list[dict]:
        return [match_row]

    async def fake_expirations() -> list[dict]:
        return [expiration_row]

    sent = {}

    async def fake_send_email(to, subject, body) -> None:
        sent["to"] = to
        sent["subject"] = subject

    stamped = {}

    async def fake_mark_notified(session_ids, request_ids) -> None:
        stamped["session_ids"] = session_ids
        stamped["request_ids"] = request_ids

    monkeypatch.setattr(matching_routes.notifications_db, "list_unnotified_matches", fake_matches)
    monkeypatch.setattr(
        matching_routes.notifications_db, "list_unnotified_expirations", fake_expirations
    )
    monkeypatch.setattr(matching_routes.email, "send_email", fake_send_email)
    monkeypatch.setattr(matching_routes.notifications_db, "mark_notified", fake_mark_notified)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json()["notified"] == 2
    assert sent["to"] == "coordinator@example.com"
    assert stamped["session_ids"] == [UUID(match_row["id"])]
    assert stamped["request_ids"] == [UUID(expiration_row["id"])]


def test_a_failed_send_stamps_nothing_and_reports_zero(monkeypatch, client: TestClient) -> None:
    _set_secret(monkeypatch)
    _set_email_config(monkeypatch)
    _patch_no_matching(monkeypatch)
    match_row = _matched_session_row()

    async def fake_matches() -> list[dict]:
        return [match_row]

    async def fake_expirations() -> list[dict]:
        return []

    async def exploding_send_email(to, subject, body) -> None:
        raise RuntimeError("Resend is down")

    async def fake_mark_notified(session_ids, request_ids) -> None:
        raise AssertionError("mark_notified should not be called when the send failed")

    monkeypatch.setattr(matching_routes.notifications_db, "list_unnotified_matches", fake_matches)
    monkeypatch.setattr(
        matching_routes.notifications_db, "list_unnotified_expirations", fake_expirations
    )
    monkeypatch.setattr(matching_routes.email, "send_email", exploding_send_email)
    monkeypatch.setattr(matching_routes.notifications_db, "mark_notified", fake_mark_notified)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json()["notified"] == 0


def test_unconfigured_coordinator_email_sends_nothing(monkeypatch, client: TestClient) -> None:
    _set_secret(monkeypatch)
    get_settings.cache_clear()
    monkeypatch.setenv("RESEND_API_KEY", "")
    monkeypatch.setenv("COORDINATOR_EMAIL", "")
    monkeypatch.setattr(matching_routes, "get_settings", get_settings)
    _patch_no_matching(monkeypatch)

    async def fake_matches() -> list[dict]:
        return [_matched_session_row()]

    async def should_not_send(to, subject, body) -> None:
        raise AssertionError("send_email should not be called when unconfigured")

    monkeypatch.setattr(matching_routes.notifications_db, "list_unnotified_matches", fake_matches)
    monkeypatch.setattr(matching_routes.email, "send_email", should_not_send)

    response = client.post("/internal/matching/run", headers={"X-Matching-Secret": "test-secret"})

    assert response.status_code == 200
    assert response.json()["notified"] == 0
