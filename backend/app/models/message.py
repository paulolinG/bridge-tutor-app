from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["tutor", "student"]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
