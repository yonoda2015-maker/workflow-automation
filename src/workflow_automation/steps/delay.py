"""DELAY step. `sleep` is injected so tests never actually wait."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from workflow_automation.models import StepResult, StepStatus

_MAX_DELAY_SECONDS = 3600  # a workflow step waiting over an hour is almost certainly a bug


@dataclass
class DelayStep:
    """step_id is a placeholder — see HttpRequestStep's docstring."""

    sleep: Callable[[float], Awaitable[None]]

    async def execute(self, config: dict[str, Any]) -> StepResult:
        seconds = config.get("seconds")
        if not isinstance(seconds, (int, float)) or seconds < 0:
            return StepResult("_", StepStatus.FAILED, error=f"invalid 'seconds': {seconds!r}")
        if seconds > _MAX_DELAY_SECONDS:
            return StepResult(
                "_",
                StepStatus.FAILED,
                error=f"delay {seconds}s exceeds {_MAX_DELAY_SECONDS}s ceiling",
            )
        await self.sleep(seconds)
        return StepResult("_", StepStatus.SUCCESS, output={"slept_seconds": seconds})
