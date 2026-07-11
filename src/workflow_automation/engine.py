"""Executes a WorkflowDef: topological order by `depends_on`, resolves templates
against prior step outputs, dispatches to the right Step implementation."""
from __future__ import annotations

from workflow_automation.models import (
    RunStatus,
    StepDef,
    StepResult,
    StepStatus,
    StepType,
    WorkflowDef,
    WorkflowRunResult,
)
from workflow_automation.steps.base import Step
from workflow_automation.templating import resolve

_MAX_STEPS_EXECUTED = 200  # matches WorkflowDef's own step-count ceiling


class CyclicWorkflowError(Exception):
    pass


def topological_order(steps: tuple[StepDef, ...]) -> list[StepDef]:
    by_id = {s.id: s for s in steps}
    visited: set[str] = set()
    in_progress: set[str] = set()
    ordered: list[StepDef] = []

    def visit(step: StepDef) -> None:
        if step.id in visited:
            return
        assert step.id not in in_progress, f"cycle detected at step {step.id!r}"
        in_progress.add(step.id)
        for dep_id in step.depends_on:
            visit(by_id[dep_id])
        in_progress.discard(step.id)
        visited.add(step.id)
        ordered.append(step)

    for step in steps:
        try:
            visit(step)
        except AssertionError as exc:
            raise CyclicWorkflowError(str(exc)) from exc
    return ordered


class WorkflowEngine:
    def __init__(self, step_factories: dict[StepType, Step]) -> None:
        """`step_factories` maps each StepType to an already-constructed Step
        (each Step instance carries its own injected call/sleep dependency)."""
        assert step_factories, "step_factories must not be empty"
        self._step_factories = step_factories

    async def run(self, workflow: WorkflowDef) -> WorkflowRunResult:
        ordered = topological_order(workflow.steps)
        assert len(ordered) <= _MAX_STEPS_EXECUTED, "step count exceeds execution ceiling"

        steps_output: dict[str, dict] = {}
        results: list[StepResult] = []
        skipped_ids: set[str] = set()

        for step_def in ordered:
            if set(step_def.depends_on) & skipped_ids:
                result = StepResult(step_def.id, StepStatus.SKIPPED)
                results.append(result)
                skipped_ids.add(step_def.id)
                continue

            step = self._step_factories.get(step_def.type)
            if step is None:
                result = StepResult(
                    step_def.id, StepStatus.FAILED, error=f"no executor for {step_def.type}"
                )
                results.append(result)
                return WorkflowRunResult(workflow.name, RunStatus.FAILED, tuple(results))

            resolved_config = resolve(step_def.config, steps_output)
            raw_result = await step.execute(resolved_config)
            # A Step instance is shared across every workflow step of its type (it's
            # constructed once with its injected dependency), so its own step_id is
            # meaningless per-invocation — always stamp the id from the actual DAG
            # node, never trust what execute() returned.
            result = StepResult(step_def.id, raw_result.status, raw_result.output, raw_result.error)
            results.append(result)

            if result.status == StepStatus.FAILED:
                return WorkflowRunResult(workflow.name, RunStatus.FAILED, tuple(results))
            if result.status == StepStatus.SKIPPED:
                skipped_ids.add(step_def.id)
                continue
            steps_output[step_def.id] = result.output

        return WorkflowRunResult(workflow.name, RunStatus.SUCCESS, tuple(results))
