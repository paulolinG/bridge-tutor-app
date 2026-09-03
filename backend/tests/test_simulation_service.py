from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.models.message import Message
from app.models.persona import Persona
from app.services import simulation

PERSONA = Persona(
    key="test",
    display_name="Test",
    microtopic_label="Math: Fractions",
    internal_system_prompt="You are a confused student.",
    student_facing_blurb="blurb",
)


def _fake_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


async def test_empty_transcript_sends_opening_prompt(monkeypatch) -> None:
    mock_client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(return_value=_fake_response("Hi!")))
    )
    monkeypatch.setattr(simulation, "get_anthropic_client", lambda: mock_client)

    reply = await simulation.generate_student_reply([], PERSONA)

    assert reply == "Hi!"
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == PERSONA.internal_system_prompt
    assert call_kwargs["messages"][0]["role"] == "user"


async def test_tutor_and_student_roles_map_to_user_and_assistant(monkeypatch) -> None:
    mock_client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(return_value=_fake_response("ok")))
    )
    monkeypatch.setattr(simulation, "get_anthropic_client", lambda: mock_client)

    transcript = [
        Message(role="student", content="Hi, I'm stuck."),
        Message(role="tutor", content="What part is confusing?"),
    ]
    await simulation.generate_student_reply(transcript, PERSONA)

    sent = mock_client.messages.create.call_args.kwargs["messages"]
    assert [m["role"] for m in sent] == ["assistant", "user"]
