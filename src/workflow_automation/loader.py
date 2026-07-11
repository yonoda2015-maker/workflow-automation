"""Parses a workflow definition dict (loaded from YAML/JSON by the caller — this
module never touches a filesystem) into a validated WorkflowDef."""
from __future__ import annotations

from typing import Any

from workflow_automation.models import StepDef, StepType, WorkflowDef


class WorkflowParseError(Exception):
    pass


def parse_workflow(data: dict[str, Any]) -> WorkflowDef:
    name = data.get("name")
    raw_steps = data.get("steps")
    if not name or not isinstance(raw_steps, list):
        raise WorkflowParseError("workflow must have a 'name' and a list of 'steps'")

    steps = []
    for raw in raw_steps:
        try:
            step_type = StepType(raw["type"])
        except (KeyError, ValueError) as exc:
            raise WorkflowParseError(f"invalid step: {raw!r} ({exc})") from exc
        steps.append(
            StepDef(
                id=raw["id"],
                type=step_type,
                config=raw.get("config", {}),
                depends_on=tuple(raw.get("depends_on", [])),
            )
        )

    try:
        return WorkflowDef(name=name, steps=tuple(steps))
    except AssertionError as exc:
        raise WorkflowParseError(str(exc)) from exc
