import pytest
from fastapi.testclient import TestClient

from app.core.supabase import get_supabase
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _block_real_supabase_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fails loudly if a test reaches the live Supabase project instead of a fake.

    `.env` holds real project credentials, so any unmocked `get_supabase()`
    call would otherwise hit production. `get_supabase` is `lru_cache`d, so a
    client built by an earlier test would silently survive into this one and
    bypass the guard below — clear the cache every test so each one is forced
    to either monkeypatch `get_supabase` itself or hit `_forbidden` here.
    Tests that legitimately exercise the db layer must monkeypatch
    `get_supabase` (or `create_client`) themselves.
    """
    get_supabase.cache_clear()

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise RuntimeError(
            "Test attempted to create a real Supabase client. Monkeypatch "
            "get_supabase() (or create_client) instead of hitting the network."
        )

    monkeypatch.setattr("app.core.supabase.create_client", _forbidden)
    yield
    get_supabase.cache_clear()
