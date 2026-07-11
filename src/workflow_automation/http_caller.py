"""Real HTTP caller used in production. Kept in its own file so tests never
import httpx — they inject a fake HttpCaller instead."""
from __future__ import annotations

from typing import Any

import httpx

_TIMEOUT_SECONDS = 30.0


async def real_http_caller(
    method: str, url: str, json_body: dict[str, Any] | None
) -> tuple[int, dict[str, Any]]:
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        response = await client.request(method, url, json=json_body)
        try:
            body = response.json()
        except ValueError:
            body = {"raw_text": response.text}
        return response.status_code, body
