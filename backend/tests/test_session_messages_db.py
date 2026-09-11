import asyncio
from uuid import uuid4

from app.db import session_messages as session_messages_db
from tests.test_matching_db import _FakeSupabaseClient

SESSION_ID = uuid4()


def test_create_message_inserts_session_role_and_content(monkeypatch) -> None:
    inserted = {
        "id": str(uuid4()),
        "session_id": str(SESSION_ID),
        "sender_role": "student",
        "content": "hi",
    }
    fake = _FakeSupabaseClient([inserted])
    monkeypatch.setattr(session_messages_db, "get_supabase", lambda: fake)

    result = asyncio.run(session_messages_db.create_message(SESSION_ID, "student", "hi"))

    assert result == inserted
    assert (
        "insert",
        {"session_id": str(SESSION_ID), "sender_role": "student", "content": "hi"},
    ) in fake.calls


def test_list_messages_filters_by_session_and_orders_ascending(monkeypatch) -> None:
    rows = [
        {"id": str(uuid4()), "session_id": str(SESSION_ID), "created_at": "2026-01-05T18:00:00Z"},
    ]
    fake = _FakeSupabaseClient(rows)
    monkeypatch.setattr(session_messages_db, "get_supabase", lambda: fake)

    result = asyncio.run(session_messages_db.list_messages(SESSION_ID))

    assert result == rows
    assert ("eq", "session_id", str(SESSION_ID)) in fake.calls
    assert ("order", "created_at") in fake.calls
