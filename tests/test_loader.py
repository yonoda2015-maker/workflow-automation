import pytest

from workflow_automation.loader import WorkflowParseError, parse_workflow
from workflow_automation.models import StepType


def test_parses_valid_workflow_dict():
    data = {
        "name": "wf",
        "steps": [
            {"id": "a", "type": "http_request", "config": {"url": "http://x"}},
            {"id": "b", "type": "transform", "config": {"mapping": {}}, "depends_on": ["a"]},
        ],
    }
    workflow = parse_workflow(data)
    assert workflow.name == "wf"
    assert workflow.steps[1].type == StepType.TRANSFORM
    assert workflow.steps[1].depends_on == ("a",)


def test_missing_name_raises():
    with pytest.raises(WorkflowParseError):
        parse_workflow({"steps": []})


def test_unknown_step_type_raises():
    data = {"name": "wf", "steps": [{"id": "a", "type": "not_a_real_type"}]}
    with pytest.raises(WorkflowParseError):
        parse_workflow(data)


def test_invalid_dag_surfaces_as_parse_error():
    data = {
        "name": "wf",
        "steps": [{"id": "a", "type": "transform", "depends_on": ["missing"]}],
    }
    with pytest.raises(WorkflowParseError):
        parse_workflow(data)
