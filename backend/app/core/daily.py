from datetime import datetime
from functools import lru_cache

import httpx

from app.core.config import get_settings

DAILY_API_BASE_URL: str = "https://api.daily.co/v1"


@lru_cache
def get_daily_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=DAILY_API_BASE_URL,
        headers={"Authorization": f"Bearer {get_settings().daily_api_key}"},
        timeout=10.0,
    )


async def create_room(name: str, exp: datetime) -> str:
    """Creates a private Daily room, or reuses one that already exists.

    Rooms are named deterministically (`bridge-<session_id>`) so two
    simultaneous first-joins converge instead of racing.

    Args:
        name: The deterministic room name.
        exp: When the room should stop admitting participants.

    Returns:
        The room's name.
    """
    response = await get_daily_client().post(
        "/rooms",
        json={
            "name": name,
            "privacy": "private",
            "properties": {
                "exp": int(exp.timestamp()),
                "enable_prejoin_ui": True,
                "eject_at_room_exp": True,
            },
        },
    )
    if response.status_code == 400 and "already exists" in response.text:
        return name
    response.raise_for_status()
    return response.json()["name"]


async def create_meeting_token(
    room_name: str, user_name: str, is_owner: bool, exp: datetime
) -> str:
    """Mints a short-lived meeting token scoped to one room.

    A room name alone is never enough to enter — every participant needs
    one of these, minted server-side.

    Args:
        room_name: The room this token is valid for.
        user_name: Display name shown to the other participant.
        is_owner: Whether this participant gets owner privileges.
        exp: When the token stops being valid.

    Returns:
        The signed JWT to hand to the Daily embed.
    """
    response = await get_daily_client().post(
        "/meeting-tokens",
        json={
            "properties": {
                "room_name": room_name,
                "user_name": user_name,
                "is_owner": is_owner,
                "exp": int(exp.timestamp()),
            }
        },
    )
    response.raise_for_status()
    return response.json()["token"]


def room_url(room_name: str) -> str:
    """Builds the joinable URL for a room on this account's Daily domain."""
    return f"https://{get_settings().daily_domain}/{room_name}"
