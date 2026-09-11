from app.core.ai_clients import get_instructor_client
from app.core.config import get_settings
from app.core.diagnostic_prompt import (
    CONCEPT_BLUEPRINT_INSTRUCTIONS,
    DIAGNOSTIC_PAIR_INSTRUCTIONS,
)
from app.models.diagnostic import ConceptBlueprint, DiagnosticPair

BLUEPRINT_MAX_TOKENS: int = 500
PAIR_MAX_TOKENS: int = 4000


async def generate_blueprint(microtopic_label: str, grade_level: str) -> ConceptBlueprint:
    """Derives the five concepts a microtopic is measured on.

    Args:
        microtopic_label: The microtopic, e.g. "Math: Fractions".
        grade_level: The student's grade level.

    Returns:
        The concept blueprint, to be stored on the microtopic and reused by
        every later session so they all measure the same thing.
    """
    settings = get_settings()
    client = get_instructor_client()

    prompt = CONCEPT_BLUEPRINT_INSTRUCTIONS.format(
        microtopic_label=microtopic_label, grade_level=grade_level
    )

    return await client.chat.completions.create(
        model=settings.anthropic_model_scoring,
        max_tokens=BLUEPRINT_MAX_TOKENS,
        response_model=ConceptBlueprint,
        messages=[{"role": "user", "content": prompt}],
    )


async def generate_pair(
    microtopic_label: str, concepts: list[str], grade_level: str
) -> DiagnosticPair:
    """Generates the Baseline Diagnostic and Exit Ticket as one matched pair.

    Both forms come from a single call so they share a blueprint. Note what is
    deliberately absent from the prompt: the student's academic average, and
    anything from the session itself. Calibrating difficulty per student would
    make two students' Delta Growth incomparable, which would in turn make the
    tutor impact page's per-microtopic average meaningless.

    Args:
        microtopic_label: The microtopic the session covers.
        concepts: The microtopic's fixed five-concept blueprint.
        grade_level: The student's grade level.

    Returns:
        Five concept slots, each holding a baseline item and its exit twin.
    """
    settings = get_settings()
    client = get_instructor_client()

    prompt = DIAGNOSTIC_PAIR_INSTRUCTIONS.format(
        microtopic_label=microtopic_label,
        grade_level=grade_level,
        concepts="\n".join(f"{index}. {concept}" for index, concept in enumerate(concepts, 1)),
    )

    return await client.chat.completions.create(
        model=settings.anthropic_model_scoring,
        max_tokens=PAIR_MAX_TOKENS,
        response_model=DiagnosticPair,
        messages=[{"role": "user", "content": prompt}],
    )
