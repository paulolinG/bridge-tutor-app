from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import AuthUser, get_current_auth_user
from app.db import tutors as tutors_db
from app.models.tutor import CreateTutorProfileRequest, TutorProfileResponse

router = APIRouter(prefix="/tutors", tags=["tutors"])


@router.post("")
async def create_tutor_profile(
    body: CreateTutorProfileRequest,
    auth_user: AuthUser = Depends(get_current_auth_user),
) -> TutorProfileResponse:
    existing = await tutors_db.get_tutor_profile(auth_user.id)
    if existing is not None:
        return TutorProfileResponse(**existing)

    if auth_user.email is None:
        raise HTTPException(status_code=400, detail="Your account has no email on file")

    row = await tutors_db.create_tutor_profile(auth_user.id, auth_user.email, body.display_name)
    return TutorProfileResponse(**row)
