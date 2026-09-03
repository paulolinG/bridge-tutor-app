from anthropic.types import MessageParam

from app.core.ai_clients import get_anthropic_client
from app.core.config import get_settings
from app.models.message import Message
from app.models.persona import Persona

MAX_REPLY_TOKENS = 300

_OPENING_PROMPT: list[MessageParam] = [
    {
        "role": "user",
        "content": "Say hello and briefly mention what you're hoping to get help with.",
    }
]


def _to_anthropic_messages(transcript: list[Message]) -> list[MessageParam]:
    return [
        {"role": "user" if message.role == "tutor" else "assistant", "content": message.content}
        for message in transcript
    ]


async def generate_student_reply(transcript: list[Message], persona: Persona) -> str:
    """Generate the AI student's next reply given the conversation so far.

    An empty transcript produces the student's opening line.
    """
    settings = get_settings()
    client = get_anthropic_client()

    messages = _to_anthropic_messages(transcript) if transcript else _OPENING_PROMPT

    response = await client.messages.create(
        model=settings.anthropic_model_student,
        max_tokens=MAX_REPLY_TOKENS,
        system=persona.internal_system_prompt,
        messages=messages,
    )

    reply = "".join(block.text for block in response.content if block.type == "text")
    if not reply.strip():
        raise RuntimeError("Claude returned an empty response for the student persona")

    return reply
