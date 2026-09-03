from pydantic import BaseModel


class Persona(BaseModel):
    key: str
    display_name: str
    microtopic_label: str
    internal_system_prompt: str
    student_facing_blurb: str
