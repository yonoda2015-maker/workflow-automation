"""HTTP_REQUEST step. The actual network call is injected (an httpx-backed
callable in production, a fake in tests) — this class never imports httpx."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from workflow_automation.models import StepResult, StepStatus

HttpCaller = Callable[[str, str, dict[str, Any] | None], Awaitable[tuple[int, dict[str, Any]]]]
"""(method, url, json_body) -> (status_code, response_json)."""

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


@dataclass
class HttpRequestStep:
    """`step_id` in the StepResult below is a placeholder — the engine always
    re-stamps it with the real DAG node id, since one Step instance is shared
    across every workflow step of its type (see engine.py)."""

    call: HttpCaller

    async def execute(self, config: dict[str, Any]) -> StepResult:
        method = str(config.get("method", "GET")).upper()
        url = config.get("url")
        if method not in _ALLOWED_METHODS:
            return StepResult("_", StepStatus.FAILED, error=f"unsupported method: {method!r}")
        if not url or not isinstance(url, str):
            return StepResult("_", StepStatus.FAILED, error="config missing 'url'")

        try:
            status_code, response_json = await self.call(method, url, config.get("body"))
        except Exception as exc:  # noqa: BLE001 - a failed HTTP call is workflow data, not a crash
            return StepResult("_", StepStatus.FAILED, error=str(exc))

        if status_code >= 400:
            return StepResult(
                "_",
                StepStatus.FAILED,
                output={"status_code": status_code, "body": response_json},
                error=f"HTTP {status_code}",
            )
        return StepResult(
            "_", StepStatus.SUCCESS, output={"status_code": status_code, "body": response_json}
        )
