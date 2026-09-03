from collections.abc import Callable
from functools import lru_cache

from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from supabase import Client, create_client


@lru_cache
def get_supabase() -> Client:
    """Service-role client. Bypasses RLS — the backend is the only thing that uses it."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


async def run_query[T](fn: Callable[[], T]) -> T:
    """Runs a sync supabase-py call off the event loop."""
    return await run_in_threadpool(fn)
