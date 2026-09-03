from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.models.message import Message
from app.models.persona import Persona
from app.models.rubric import RubricScore
from app.services import scoring

PERSONA = Persona(
    key="test",
    display_name="Test",
    microtopic_label="Math: Fractions",
    internal_system_prompt="You are a confused student.",
    student_facing_blurb="A confused student.",
)


async def test_score_transcript_returns_instructor_result(monkeypatch) -> None:
    expected = RubricScore(
        subject_knowledge=15,
        subject_knowledge_rationale="r",
        instructional_quality=30,
        instructional_quality_rationale="r",
        pedagogical_adaptability=15,
        pedagogical_adaptability_rationale="r",
        organization=15,
        organization_rationale="r",
    )
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=expected)))
    )
    monkeypatch.setattr(scoring, "get_instructor_client", lambda: mock_client)

    transcript = [
        Message(role="tutor", content="Let's add 1/2 and 1/3."),
        Message(role="student", content="I don't get common denominators."),
    ]
    result = await scoring.score_transcript(transcript, PERSONA)

    assert result is expected
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_model"] is RubricScore
    prompt = call_kwargs["messages"][0]["content"]
    assert "Tutor: Let's add 1/2 and 1/3." in prompt
    assert "Student: I don't get common denominators." in prompt
    assert PERSONA.display_name in prompt
