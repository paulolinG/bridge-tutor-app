from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from starlette.concurrency import run_in_threadpool
from supabase_auth.errors import AuthError

from app.core.supabase import get_supabase


@dataclass
class AuthUser:
    id: UUID
    email: str | None


async def get_current_auth_user(authorization: str | None = Header(default=None)) -> AuthUser:
    """Resolves the requesting user from a Supabase JWT in the Authorization header."""
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.removeprefix("Bearer ").strip()

    def _get_user() -> AuthUser:
        try:
            response = get_supabase().auth.get_user(token)
        except AuthError as exc:
            raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
        if response.user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return AuthUser(id=UUID(response.user.id), email=response.user.email)

    return await run_in_threadpool(_get_user)


async def get_current_tutor(auth_user: AuthUser = Depends(get_current_auth_user)) -> UUID:
    return auth_user.id
