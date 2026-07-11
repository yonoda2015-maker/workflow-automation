"""TRANSFORM step: builds a new named output from already-resolved template
expressions. All the real work (looking up `{{steps...}}` values) happens in the
engine's generic templating pass before `execute` ever runs — this step is
deliberately just "hand the resolved mapping back as output."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workflow_automation.models import StepResult, StepStatus


@dataclass
class TransformStep:
    """step_id is a placeholder — see HttpRequestStep's docstring."""

    async def execute(self, config: dict[str, Any]) -> StepResult:
        mapping = config.get("mapping")
        if not isinstance(mapping, dict):
            return StepResult("_", StepStatus.FAILED, error="config missing dict 'mapping'")
        return StepResult("_", StepStatus.SUCCESS, output=dict(mapping))
