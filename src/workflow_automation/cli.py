"""CLI: validate a workflow file, run it, or list past runs."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import yaml

from workflow_automation.engine import WorkflowEngine
from workflow_automation.http_caller import real_http_caller
from workflow_automation.loader import parse_workflow
from workflow_automation.models import RunStatus, StepType
from workflow_automation.steps.condition import ConditionStep
from workflow_automation.steps.delay import DelayStep
from workflow_automation.steps.http_request import HttpRequestStep
from workflow_automation.steps.transform import TransformStep
from workflow_automation.storage import RunHistory


def _load_workflow(path: Path):
    data = yaml.safe_load(path.read_text())
    return parse_workflow(data)


def _build_engine() -> WorkflowEngine:
    return WorkflowEngine(
        {
            StepType.HTTP_REQUEST: HttpRequestStep(real_http_caller),
            StepType.TRANSFORM: TransformStep(),
            StepType.CONDITION: ConditionStep(),
            StepType.DELAY: DelayStep(asyncio.sleep),
        }
    )


async def _run(workflow_path: Path, db_path: Path) -> None:
    workflow = _load_workflow(workflow_path)
    engine = _build_engine()
    result = await engine.run(workflow)

    history = RunHistory(db_path)
    run_id = history.record(result)
    history.close()

    print(f"Run #{run_id}: {result.workflow_name} -> {result.status.value}")
    for step_result in result.step_results:
        print(f"  [{step_result.status.value}] {step_result.step_id}: {step_result.output or step_result.error}")


def _validate(workflow_path: Path) -> None:
    workflow = _load_workflow(workflow_path)
    print(f"OK: '{workflow.name}' with {len(workflow.steps)} step(s)")


def _list_runs(db_path: Path, workflow_name: str | None) -> None:
    history = RunHistory(db_path)
    runs = history.list_runs(workflow_name=workflow_name)
    history.close()
    print(json.dumps(runs, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="workflow-automation")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_p = sub.add_parser("validate")
    validate_p.add_argument("workflow_file", type=Path)

    run_p = sub.add_parser("run")
    run_p.add_argument("workflow_file", type=Path)
    run_p.add_argument("--db", type=Path, default=Path("runs.db"))

    list_p = sub.add_parser("list-runs")
    list_p.add_argument("--db", type=Path, default=Path("runs.db"))
    list_p.add_argument("--workflow-name", default=None)

    args = parser.parse_args()
    if args.command == "validate":
        _validate(args.workflow_file)
    elif args.command == "run":
        asyncio.run(_run(args.workflow_file, args.db))
    else:
        _list_runs(args.db, args.workflow_name)


if __name__ == "__main__":
    main()
