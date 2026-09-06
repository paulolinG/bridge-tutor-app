from typing import Any

from pydantic import BaseModel, Field, computed_field

CATEGORIES = (
    "subject_knowledge",
    "instructional_quality",
    "pedagogical_adaptability",
    "organization",
)

PASSING_SCORE: int = 70


class RubricScore(BaseModel):
    subject_knowledge: int = Field(ge=0, le=20)
    subject_knowledge_rationale: str
    instructional_quality: int = Field(ge=0, le=40)
    instructional_quality_rationale: str
    pedagogical_adaptability: int = Field(ge=0, le=20)
    pedagogical_adaptability_rationale: str
    organization: int = Field(ge=0, le=20)
    organization_rationale: str

    @computed_field
    @property
    def total_score(self) -> int:
        return sum(getattr(self, category) for category in CATEGORIES)

    @computed_field
    @property
    def passed(self) -> bool:
        return self.total_score >= PASSING_SCORE

    def to_row(self) -> dict[str, Any]:
        """Flattens into the tutor_certifications column shape."""
        row: dict[str, Any] = {}
        for category in CATEGORIES:
            row[f"{category}_score"] = getattr(self, category)
            row[f"{category}_rationale"] = getattr(self, f"{category}_rationale")
        return row

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "RubricScore":
        """Reconstructs from a tutor_certifications row. Inverse of to_row()."""
        fields: dict[str, Any] = {}
        for category in CATEGORIES:
            fields[category] = row[f"{category}_score"]
            fields[f"{category}_rationale"] = row[f"{category}_rationale"]
        return cls(**fields)
