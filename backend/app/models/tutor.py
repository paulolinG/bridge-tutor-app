from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

CertificationStatus = Literal["not_started", "in_progress", "passed", "failed"]


class CreateTutorProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)


class TutorProfileResponse(BaseModel):
    id: UUID
    display_name: str
    email: str
    certification_status: CertificationStatus
