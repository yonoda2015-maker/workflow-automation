"""Core data types. A workflow is a DAG of steps; frozen dataclasses + enums keep
invalid workflows (cycles, unknown step types, bad configs) from being constructed
in the first place rather than discovered mid-run."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

_MAX_STEPS_PER_WORKFLOW = 200  # a workflow with more steps than this is a design smell


class StepType(enum.Enum):
    HTTP_REQUEST = "http_request"
    TRANSFORM = "transform"
    CONDITION = "condition"
    DELAY = "delay"


@dataclass(frozen=True, slots=True)
class StepDef:
    id: str
    type: StepType
    config: dict[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        assert self.id, "step id must not be empty"
        assert self.id not in self.depends_on, f"step {self.id!r} cannot depend on itself"


@dataclass(frozen=True, slots=True)
class WorkflowDef:
    name: str
    steps: tuple[StepDef, ...]

    def __post_init__(self) -> None:
        assert self.name, "workflow name must not be empty"
        assert self.steps, "workflow must have at least one step"
        assert len(self.steps) <= _MAX_STEPS_PER_WORKFLOW, (
            f"workflow has {len(self.steps)} steps, over the {_MAX_STEPS_PER_WORKFLOW} ceiling"
        )
        ids = [s.id for s in self.steps]
        assert len(ids) == len(set(ids)), f"duplicate step ids in workflow: {ids}"
        known_ids = set(ids)
        for step in self.steps:
            unknown = set(step.depends_on) - known_ids
            assert not unknown, f"step {step.id!r} depends on unknown step(s): {unknown}"


class StepStatus(enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"  # e.g. a CONDITION step's branch that didn't match


@dataclass(frozen=True, slots=True)
class StepResult:
    step_id: str
    status: StepStatus
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        if self.status == StepStatus.FAILED:
            assert self.error, "a FAILED step result must carry an error message"


class RunStatus(enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class WorkflowRunResult:
    workflow_name: str
    status: RunStatus
    step_results: tuple[StepResult, ...] = ()
