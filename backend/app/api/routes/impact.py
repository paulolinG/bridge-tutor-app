from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_tutor
from app.db import impact as impact_db
from app.models.impact import TutorImpactResponse, TutorSessionRow
from app.services import impact as impact_service

router = APIRouter(prefix="/tutors/me/impact", tags=["impact"])


@router.get("")
async def get_my_impact(tutor_id: UUID = Depends(get_current_tutor)) -> TutorImpactResponse:
    """The tutor's aggregate volunteer impact record."""
    rows = await impact_db.list_tutor_sessions(tutor_id)
    return impact_service.build_impact([TutorSessionRow.from_row(row) for row in rows])
