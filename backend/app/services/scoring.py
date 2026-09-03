from app.core.ai_clients import get_instructor_client
from app.core.config import get_settings
from app.core.rubric_prompt import RUBRIC_SCORING_INSTRUCTIONS
from app.models.message import Message
from app.models.persona import Persona
from app.models.rubric import RubricScore


def _format_transcript(transcript: list[Message]) -> str:
    speaker = {"tutor": "Tutor", "student": "Student"}
    return "\n".join(f"{speaker[message.role]}: {message.content}" for message in transcript)


async def score_transcript(transcript: list[Message], persona: Persona) -> RubricScore:
    settings = get_settings()
    client = get_instructor_client()

    prompt = RUBRIC_SCORING_INSTRUCTIONS.format(
        persona_display_name=persona.display_name,
        persona_description=persona.student_facing_blurb,
        transcript=_format_transcript(transcript),
    )

    return await client.chat.completions.create(
        model=settings.anthropic_model_scoring,
        max_tokens=1500,
        response_model=RubricScore,
        messages=[{"role": "user", "content": prompt}],
    )
