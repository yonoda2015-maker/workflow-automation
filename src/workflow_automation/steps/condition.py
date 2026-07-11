"""CONDITION step: compares two already-resolved values with an operator. No
eval() — a fixed, closed set of operators is the entire language surface, which
is what keeps a workflow file from becoming an arbitrary-code-execution vector."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workflow_automation.models import StepResult, StepStatus

_OPERATORS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
}


@dataclass
class ConditionStep:
    """step_id is a placeholder — see HttpRequestStep's docstring."""

    async def execute(self, config: dict[str, Any]) -> StepResult:
        operator = config.get("operator", "==")
        if operator not in _OPERATORS:
            return StepResult("_", StepStatus.FAILED, error=f"unsupported operator: {operator!r}")
        left, right = config.get("left"), config.get("right")
        try:
            matched = _OPERATORS[operator](left, right)
        except TypeError as exc:
            return StepResult("_", StepStatus.FAILED, error=str(exc))

        status = StepStatus.SUCCESS if matched else StepStatus.SKIPPED
        return StepResult("_", status, output={"matched": matched})
