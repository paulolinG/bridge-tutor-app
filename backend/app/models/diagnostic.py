from typing import Any, Literal

from pydantic import BaseModel, Field

ITEMS_PER_FORM: int = 5
OPTIONS_PER_ITEM: int = 4
DEFAULT_GRADE_LEVEL: str = "Grade 9"

BASELINE: str = "baseline"
EXIT: str = "exit"

DiagnosticKind = Literal["baseline", "exit"]


class DiagnosticItem(BaseModel):
    """One auto-scored multiple-choice item, answer key included."""

    prompt: str
    options: list[str] = Field(min_length=OPTIONS_PER_ITEM, max_length=OPTIONS_PER_ITEM)
    correct_index: int = Field(ge=0, le=OPTIONS_PER_ITEM - 1)


class ConceptSlot(BaseModel):
    """One concept, measured by a matched pair of items.

    Pairing lives in the schema rather than in the prompt: with both items
    owned by the slot, there is no well-formed response in which the baseline
    and the exit ticket cover different concepts.
    """

    concept: str
    baseline: DiagnosticItem
    exit: DiagnosticItem


class DiagnosticPair(BaseModel):
    slots: list[ConceptSlot] = Field(min_length=ITEMS_PER_FORM, max_length=ITEMS_PER_FORM)

    def items_for(self, kind: str) -> list[dict[str, Any]]:
        """Flattens one side of the pair into storable item rows."""
        return [
            {"concept": slot.concept, **getattr(slot, kind).model_dump()} for slot in self.slots
        ]


class ConceptBlueprint(BaseModel):
    concepts: list[str] = Field(min_length=ITEMS_PER_FORM, max_length=ITEMS_PER_FORM)


class DiagnosticItemResponse(BaseModel):
    """An item as the student sees it. Exists so `correct_index` cannot leak."""

    prompt: str
    options: list[str]


class DiagnosticFormResponse(BaseModel):
    kind: DiagnosticKind
    items: list[DiagnosticItemResponse]


class CurrentDiagnosticResponse(BaseModel):
    form: DiagnosticFormResponse | None


class SubmitDiagnosticRequest(BaseModel):
    answers: list[int] = Field(min_length=ITEMS_PER_FORM, max_length=ITEMS_PER_FORM)


class SubmitDiagnosticResponse(BaseModel):
    submitted: bool


class BaselineScoreResponse(BaseModel):
    """The tutor's view of the baseline: the score only, never the items.

    The forms are a matched blueprint, so showing a tutor the baseline items
    is functionally showing them the exit ticket — and a tutor who drills
    those exact items inflates every average on their impact page.
    """

    score_percent: float | None
