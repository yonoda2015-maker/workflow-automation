import pytest

from workflow_automation.models import StepDef, StepType, WorkflowDef


def _step(id_, depends_on=()):
    return StepDef(id=id_, type=StepType.TRANSFORM, config={}, depends_on=depends_on)


def test_workflow_requires_at_least_one_step():
    with pytest.raises(AssertionError):
        WorkflowDef(name="w", steps=())


def test_duplicate_step_ids_rejected():
    with pytest.raises(AssertionError):
        WorkflowDef(name="w", steps=(_step("a"), _step("a")))


def test_unknown_dependency_rejected():
    with pytest.raises(AssertionError):
        WorkflowDef(name="w", steps=(_step("a", depends_on=("missing",)),))


def test_self_dependency_rejected():
    with pytest.raises(AssertionError):
        _step("a", depends_on=("a",))


def test_valid_workflow_constructs():
    wf = WorkflowDef(name="w", steps=(_step("a"), _step("b", depends_on=("a",))))
    assert len(wf.steps) == 2
