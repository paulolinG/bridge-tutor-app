from functools import lru_cache

import httpx

from app.core.config import get_settings

RESEND_API_BASE_URL: str = "https://api.resend.com"

# `onboarding@resend.dev` needs no domain and no DNS, but Resend restricts it
# to delivering only to the account's own address — see
# https://resend.com/docs/knowledge-base/403-error-resend-dev-domain. That
# restriction is exactly the Coordinator Digest's single-recipient design;
# lifting it for a second coordinator address would require verifying a
# real domain first.
FROM_ADDRESS: str = "Bridge AI <onboarding@resend.dev>"


@lru_cache
def get_email_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=RESEND_API_BASE_URL,
        headers={"Authorization": f"Bearer {get_settings().resend_api_key}"},
        timeout=10.0,
    )


async def send_email(to: str, subject: str, body: str) -> None:
    """Sends a plain-text email via Resend.

    Raises rather than swallows: the caller decides whether a failed send
    is survivable (it is, for the Coordinator Digest — the next hourly run
    retries), the adapter has no opinion of its own.

    Args:
        to: The recipient address.
        subject: The email subject line.
        body: The plain-text body.

    Raises:
        httpx.HTTPStatusError: If Resend rejects or fails to send the email.
    """
    response = await get_email_client().post(
        "/emails",
        json={"from": FROM_ADDRESS, "to": [to], "subject": subject, "text": body},
    )
    response.raise_for_status()
