import pytest

from workflow_automation.engine import CyclicWorkflowError, WorkflowEngine, topological_order
from workflow_automation.models import RunStatus, StepDef, StepStatus, StepType, WorkflowDef
from workflow_automation.steps.condition import ConditionStep
from workflow_automation.steps.delay import DelayStep
from workflow_automation.steps.http_request import HttpRequestStep
from workflow_automation.steps.transform import TransformStep


async def _no_op_sleep(_seconds: float) -> None:
    return None


def _make_engine(http_caller=None):
    return WorkflowEngine(
        {
            StepType.HTTP_REQUEST: HttpRequestStep(http_caller or (lambda *_: None)),
            StepType.TRANSFORM: TransformStep(),
            StepType.CONDITION: ConditionStep(),
            StepType.DELAY: DelayStep(_no_op_sleep),
        }
    )


def test_topological_order_respects_dependencies():
    a = StepDef(id="a", type=StepType.TRANSFORM, config={"mapping": {}})
    b = StepDef(id="b", type=StepType.TRANSFORM, config={"mapping": {}}, depends_on=("a",))
    c = StepDef(id="c", type=StepType.TRANSFORM, config={"mapping": {}}, depends_on=("b",))
    ordered = topological_order((c, a, b))
    assert [s.id for s in ordered] == ["a", "b", "c"]


def test_cyclic_workflow_detected():
    a = StepDef(id="a", type=StepType.TRANSFORM, config={}, depends_on=("b",))
    b = StepDef(id="b", type=StepType.TRANSFORM, config={}, depends_on=("a",))
    with pytest.raises(CyclicWorkflowError):
        topological_order((a, b))


@pytest.mark.asyncio
async def test_http_then_transform_pipes_output_through_templating():
    async def fake_caller(method, url, body):
        assert method == "GET"
        return 200, {"value": 42}

    engine = _make_engine(fake_caller)
    workflow = WorkflowDef(
        name="wf",
        steps=(
            StepDef(id="fetch", type=StepType.HTTP_REQUEST, config={"method": "GET", "url": "http://x"}),
            StepDef(
                id="summarize",
                type=StepType.TRANSFORM,
                config={"mapping": {"v": "{{steps.fetch.output.body.value}}"}},
                depends_on=("fetch",),
            ),
        ),
    )
    result = await engine.run(workflow)
    assert result.status == RunStatus.SUCCESS
    summarize_result = result.step_results[1]
    assert summarize_result.output == {"v": 42}


@pytest.mark.asyncio
async def test_http_failure_stops_the_workflow():
    async def failing_caller(method, url, body):
        raise ConnectionError("unreachable")

    engine = _make_engine(failing_caller)
    workflow = WorkflowDef(
        name="wf",
        steps=(
            StepDef(id="fetch", type=StepType.HTTP_REQUEST, config={"method": "GET", "url": "http://x"}),
            StepDef(
                id="never_runs",
                type=StepType.TRANSFORM,
                config={"mapping": {}},
                depends_on=("fetch",),
            ),
        ),
    )
    result = await engine.run(workflow)
    assert result.status == RunStatus.FAILED
    assert len(result.step_results) == 1  # never_runs must not have executed


@pytest.mark.asyncio
async def test_condition_false_skips_dependents():
    engine = _make_engine()
    workflow = WorkflowDef(
        name="wf",
        steps=(
            StepDef(
                id="check", type=StepType.CONDITION, config={"left": 1, "operator": "==", "right": 2}
            ),
            StepDef(
                id="downstream",
                type=StepType.TRANSFORM,
                config={"mapping": {}},
                depends_on=("check",),
            ),
        ),
    )
    result = await engine.run(workflow)
    assert result.status == RunStatus.SUCCESS
    statuses = {r.step_id: r.status for r in result.step_results}
    assert statuses["check"] == StepStatus.SKIPPED
    assert statuses["downstream"] == StepStatus.SKIPPED


@pytest.mark.asyncio
async def test_delay_step_uses_injected_sleep_not_real_time():
    calls = []

    async def recording_sleep(seconds):
        calls.append(seconds)

    engine = WorkflowEngine({StepType.DELAY: DelayStep(recording_sleep)})
    workflow = WorkflowDef(
        name="wf", steps=(StepDef(id="wait", type=StepType.DELAY, config={"seconds": 5}),)
    )
    result = await engine.run(workflow)
    assert result.status == RunStatus.SUCCESS
    assert calls == [5]
