from uuid import UUID

from fastapi import Header, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.supabase import get_supabase


async def get_current_tutor(authorization: str | None = Header(default=None)) -> UUID:
    """Resolves the requesting tutor's id.

    Reads a Supabase JWT from the Authorization header when present. Falls back to
    DEV_AUTH_BYPASS_TUTOR_ID when absent, since this pass has no login/signup UI yet —
    swap this out for hard JWT enforcement once auth pages land, no route signatures change.
    """
    settings = get_settings()

    if authorization is None:
        if settings.dev_auth_bypass_tutor_id:
            return UUID(settings.dev_auth_bypass_tutor_id)
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.removeprefix("Bearer ").strip()

    def _get_user() -> UUID:
        response = get_supabase().auth.get_user(token)
        if response.user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return UUID(response.user.id)

    return await run_in_threadpool(_get_user)
