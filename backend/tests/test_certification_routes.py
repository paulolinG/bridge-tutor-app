from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import certification as certification_routes
from app.core.personas import PERSONAS
from app.main import app
from app.models.rubric import RubricScore

TUTOR_ID = uuid4()
OTHER_TUTOR_ID = uuid4()
MICROTOPIC_ID = uuid4()
CERT_ID = uuid4()
PERSONA_KEY = next(iter(PERSONAS))
PERSONA = PERSONAS[PERSONA_KEY]


@pytest.fixture(autouse=True)
def _bypass_auth():
    async def fake_get_current_tutor() -> object:
        return TUTOR_ID

    app.dependency_overrides[deps.get_current_tutor] = fake_get_current_tutor
    yield
    app.dependency_overrides.clear()


def _row(
    status: str = "in_progress",
    transcript: list[dict] | None = None,
    version: int = 0,
    persona_key: str = PERSONA_KEY,
    **scores: object,
) -> dict:
    return {
        "id": str(CERT_ID),
        "tutor_id": str(TUTOR_ID),
        "microtopic_id": str(MICROTOPIC_ID),
        "persona_key": persona_key,
        "transcript": transcript or [],
        "version": version,
        "status": status,
        "subject_knowledge_score": scores.get("subject_knowledge_score"),
        "subject_knowledge_rationale": scores.get("subject_knowledge_rationale"),
        "instructional_quality_score": scores.get("instructional_quality_score"),
        "instructional_quality_rationale": scores.get("instructional_quality_rationale"),
        "pedagogical_adaptability_score": scores.get("pedagogical_adaptability_score"),
        "pedagogical_adaptability_rationale": scores.get("pedagogical_adaptability_rationale"),
        "organization_score": scores.get("organization_score"),
        "organization_rationale": scores.get("organization_rationale"),
    }


def _six_turn_transcript() -> list[dict]:
    turns = []
    for i in range(6):
        turns.append({"role": "tutor", "content": f"tutor turn {i}"})
        turns.append({"role": "student", "content": f"student turn {i}"})
    return turns


def test_start_certification(monkeypatch, client: TestClient) -> None:
    async def fake_get_microtopic(microtopic_id: object) -> dict:
        return {
            "id": str(MICROTOPIC_ID),
            "subject": "Math",
            "topic": "Fractions",
            "label": PERSONA.microtopic_label,
        }

    async def fake_generate_student_reply(transcript: list, persona: object) -> str:
        return "Hi, I'm stuck on fractions."

    async def fake_create_certification(
        tutor_id: object, microtopic_id: object, persona_key: str
    ) -> dict:
        return _row()

    async def fake_append_message(
        certification_id: object, transcript: list, expected_version: int
    ) -> bool:
        return True

    monkeypatch.setattr(certification_routes, "get_microtopic", fake_get_microtopic)
    monkeypatch.setattr(certification_routes, "generate_student_reply", fake_generate_student_reply)
    monkeypatch.setattr(
        certification_routes.certifications_db, "create_certification", fake_create_certification
    )
    monkeypatch.setattr(
        certification_routes.certifications_db, "append_message", fake_append_message
    )

    response = client.post("/certifications", json={"microtopic_id": str(MICROTOPIC_ID)})

    assert response.status_code == 200
    body = response.json()
    assert body["certification_id"] == str(CERT_ID)
    assert body["opening_message"] == "Hi, I'm stuck on fractions."
    assert body["min_turns_to_end"] == certification_routes.MIN_TURNS_TO_END
    assert body["max_turns"] == certification_routes.MAX_TURNS


def test_start_certification_unknown_microtopic_label_returns_404(
    monkeypatch, client: TestClient
) -> None:
    async def fake_get_microtopic(microtopic_id: object) -> dict:
        return {
            "id": str(MICROTOPIC_ID),
            "subject": "Chemistry",
            "topic": "Stoichiometry",
            "label": "Chemistry: Stoichiometry",
        }

    monkeypatch.setattr(certification_routes, "get_microtopic", fake_get_microtopic)

    response = client.post("/certifications", json={"microtopic_id": str(MICROTOPIC_ID)})

    assert response.status_code == 404


def test_send_message_appends_turn(monkeypatch, client: TestClient) -> None:
    async def fake_get_certification(certification_id: object) -> dict:
        return _row(transcript=[{"role": "student", "content": "Hi"}], version=3)

    async def fake_generate_student_reply(transcript: list, persona: object) -> str:
        return "Still confused."

    async def fake_append_message(
        certification_id: object, transcript: list, expected_version: int
    ) -> bool:
        assert expected_version == 3
        return True

    monkeypatch.setattr(
        certification_routes.certifications_db, "get_certification", fake_get_certification
    )
    monkeypatch.setattr(certification_routes, "generate_student_reply", fake_generate_student_reply)
    monkeypatch.setattr(
        certification_routes.certifications_db, "append_message", fake_append_message
    )

    response = client.post(f"/certifications/{CERT_ID}/messages", json={"content": "Try 1/2 + 1/3"})

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Still confused."
    assert body["turn_count"] == 1


def test_send_message_conflict_on_concurrent_write(monkeypatch, client: TestClient) -> None:
    async def fake_get_certification(certification_id: object) -> dict:
        return _row(transcript=[{"role": "student", "content": "Hi"}], version=3)

    async def fake_generate_student_reply(transcript: list, persona: object) -> str:
        return "Still confused."

    async def fake_append_message(
        certification_id: object, transcript: list, expected_version: int
    ) -> bool:
        return False

    monkeypatch.setattr(
        certification_routes.certifications_db, "get_certification", fake_get_certification
    )
    monkeypatch.setattr(certification_routes, "generate_student_reply", fake_generate_student_reply)
    monkeypatch.setattr(
        certification_routes.certifications_db, "append_message", fake_append_message
    )

    response = client.post(f"/certifications/{CERT_ID}/messages", json={"content": "hi"})

    assert response.status_code == 409


def test_send_message_rejects_blank_content(client: TestClient) -> None:
    response = client.post(f"/certifications/{CERT_ID}/messages", json={"content": "   "})

    assert response.status_code == 422


def test_send_message_rejects_other_tutors_certification(monkeypatch, client: TestClient) -> None:
    async def fake_get_certification(certification_id: object) -> dict:
        row = _row()
        row["tutor_id"] = str(OTHER_TUTOR_ID)
        return row

    monkeypatch.setattr(
        certification_routes.certifications_db, "get_certification", fake_get_certification
    )

    response = client.post(f"/certifications/{CERT_ID}/messages", json={"content": "hi"})

    assert response.status_code == 403


def test_send_message_unknown_persona_key_returns_500_not_crash(
    monkeypatch, client: TestClient
) -> None:
    async def fake_get_certification(certification_id: object) -> dict:
        return _row(persona_key="retired_persona")

    monkeypatch.setattr(
        certification_routes.certifications_db, "get_certification", fake_get_certification
    )

    response = client.post(f"/certifications/{CERT_ID}/messages", json={"content": "hi"})

    assert response.status_code == 500


def test_end_certification_rejects_too_few_turns(monkeypatch, client: TestClient) -> None:
    async def fake_get_certification(certification_id: object) -> dict:
        return _row(transcript=[{"role": "tutor", "content": "hi"}])

    monkeypatch.setattr(
        certification_routes.certifications_db, "get_certification", fake_get_certification
    )

    response = client.post(f"/certifications/{CERT_ID}/end")

    assert response.status_code == 400


def test_end_certification_passing_score_persists_competency(
    monkeypatch, client: TestClient
) -> None:
    passing_score = RubricScore(
        subject_knowledge=18,
        subject_knowledge_rationale="strong",
        instructional_quality=35,
        instructional_quality_rationale="clear",
        pedagogical_adaptability=18,
        pedagogical_adaptability_rationale="checked understanding",
        organization=15,
        organization_rationale="structured",
    )

    async def fake_get_certification(certification_id: object) -> dict:
        return _row(transcript=_six_turn_transcript())

    async def fake_score_transcript(transcript: list, persona: object) -> RubricScore:
        return passing_score

    calls: list[str] = []

    async def fake_mark_completed(certification_id: object, score: RubricScore) -> None:
        calls.append("mark_completed")

    async def fake_upsert_competency(
        tutor_id: object, microtopic_id: object, certification_id: object
    ) -> None:
        calls.append("upsert_competency")

    async def fake_update_status(tutor_id: object, status: str) -> None:
        calls.append(f"status:{status}")

    monkeypatch.setattr(
        certification_routes.certifications_db, "get_certification", fake_get_certification
    )
    monkeypatch.setattr(certification_routes, "score_transcript", fake_score_transcript)
    monkeypatch.setattr(
        certification_routes.certifications_db, "mark_completed", fake_mark_completed
    )
    monkeypatch.setattr(
        certification_routes.certifications_db, "upsert_competency", fake_upsert_competency
    )
    monkeypatch.setattr(
        certification_routes.certifications_db,
        "update_tutor_certification_status",
        fake_update_status,
    )

    response = client.post(f"/certifications/{CERT_ID}/end")

    assert response.status_code == 200
    assert response.json()["score"]["passed"] is True
    # mark_completed (which flips status to "completed") must run last, after the
    # credit-granting writes succeed, so a failure there leaves the row retryable.
    assert calls[-1] == "mark_completed"
    assert set(calls) == {"mark_completed", "upsert_competency", "status:passed"}


def test_get_certification_state_returns_score_when_completed(
    monkeypatch, client: TestClient
) -> None:
    async def fake_get_certification(certification_id: object) -> dict:
        return _row(
            status="completed",
            transcript=[{"role": "student", "content": "Hi"}],
            subject_knowledge_score=18,
            subject_knowledge_rationale="strong",
            instructional_quality_score=35,
            instructional_quality_rationale="clear",
            pedagogical_adaptability_score=18,
            pedagogical_adaptability_rationale="checked",
            organization_score=15,
            organization_rationale="structured",
        )

    monkeypatch.setattr(
        certification_routes.certifications_db, "get_certification", fake_get_certification
    )

    response = client.get(f"/certifications/{CERT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["score"]["total_score"] == 86
    assert body["score"]["passed"] is True
    assert body["min_turns_to_end"] == certification_routes.MIN_TURNS_TO_END
