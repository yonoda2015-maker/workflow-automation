from workflow_automation.models import RunStatus, StepResult, StepStatus, WorkflowRunResult
from workflow_automation.storage import RunHistory


def test_record_and_list_runs(tmp_path):
    history = RunHistory(tmp_path / "runs.db")
    result = WorkflowRunResult(
        workflow_name="wf",
        status=RunStatus.SUCCESS,
        step_results=(StepResult("a", StepStatus.SUCCESS, output={"x": 1}),),
    )
    run_id = history.record(result)
    assert run_id == 1

    runs = history.list_runs()
    assert len(runs) == 1
    assert runs[0]["workflow_name"] == "wf"
    assert runs[0]["status"] == "success"
    history.close()


def test_count_by_status(tmp_path):
    history = RunHistory(tmp_path / "runs.db")
    history.record(WorkflowRunResult("wf", RunStatus.SUCCESS))
    history.record(WorkflowRunResult("wf", RunStatus.FAILED))
    assert history.count() == 2
    assert history.count(status=RunStatus.SUCCESS) == 1
    history.close()


def test_list_runs_filters_by_workflow_name(tmp_path):
    history = RunHistory(tmp_path / "runs.db")
    history.record(WorkflowRunResult("a", RunStatus.SUCCESS))
    history.record(WorkflowRunResult("b", RunStatus.SUCCESS))
    runs = history.list_runs(workflow_name="a")
    assert len(runs) == 1
    assert runs[0]["workflow_name"] == "a"
    history.close()
