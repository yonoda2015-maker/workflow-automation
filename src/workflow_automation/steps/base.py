"""Step protocol. Adding a new step type = one class implementing `execute`, same
adapter pattern as the other two portfolio projects — the engine never changes."""
from __future__ import annotations

from typing import Any, Protocol

from workflow_automation.models import StepResult


class Step(Protocol):
    async def execute(self, config: dict[str, Any]) -> StepResult:
        """`config` has already had all `{{steps...}}` templates resolved by the
        engine — a Step implementation never needs to know templating exists."""
        ...
