from fastapi import APIRouter

from app.db.microtopics import list_microtopics
from app.models.microtopic import Microtopic

router = APIRouter()


@router.get("/microtopics")
async def get_microtopics() -> list[Microtopic]:
    rows = await list_microtopics()
    return [Microtopic.model_validate(row) for row in rows]
