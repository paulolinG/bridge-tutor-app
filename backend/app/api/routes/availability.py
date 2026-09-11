from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_tutor
from app.db import availability as availability_db
from app.db import tutors as tutors_db
from app.models.availability import AvailabilityResponse, UpdateAvailabilityRequest

router = APIRouter(prefix="/tutors/me/availability", tags=["availability"])


@router.get("")
async def get_availability(tutor_id: UUID = Depends(get_current_tutor)) -> AvailabilityResponse:
    windows = await availability_db.get_availability_windows(tutor_id)
    profile = await tutors_db.get_tutor_profile(tutor_id)
    return AvailabilityResponse(
        windows=windows,
        daily_cap_minutes=profile["daily_cap_minutes"] if profile else None,
        weekly_cap_minutes=profile["weekly_cap_minutes"] if profile else None,
    )


@router.put("")
async def update_availability(
    body: UpdateAvailabilityRequest,
    tutor_id: UUID = Depends(get_current_tutor),
) -> AvailabilityResponse:
    """Replaces a tutor's availability windows and capacity caps.

    Completing this form is what makes a certified tutor eligible for the
    Matching Engine's domain — a tutor with no caps set is never a candidate.
    """
    await availability_db.replace_availability_windows(
        tutor_id, [window.model_dump() for window in body.windows]
    )
    await availability_db.update_capacity(tutor_id, body.daily_cap_minutes, body.weekly_cap_minutes)
    return AvailabilityResponse(
        windows=body.windows,
        daily_cap_minutes=body.daily_cap_minutes,
        weekly_cap_minutes=body.weekly_cap_minutes,
    )
