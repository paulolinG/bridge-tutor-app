from uuid import UUID

from pydantic import BaseModel


class Microtopic(BaseModel):
    id: UUID
    subject: str
    topic: str
    label: str
