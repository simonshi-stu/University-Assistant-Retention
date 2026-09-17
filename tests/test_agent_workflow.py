from __future__ import annotations

import json
from pathlib import Path

import pytest

from course_retention.agent_workflow import (
    AgentWorkflow,
    AuditVerificationError,
    DuplicateExecutionError,
    InvalidTransitionError,
    PathViolationError,
    WorkflowError,
)


class FakeResponse:
    def __init__(self, content: str = "diff --git a/a.py b/a.py") -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "id": "response-1",
            "model": "deepseek-flash",
            "choices": [{"message": {"content": self.content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }


def make_workflow(tmp_path: Path, *, post=None) -> AgentWorkflow:
    (tmp_path / "src").mkdir(exist_ok=True)
    return AgentWorkflow(
        tmp_path,
        http_post=post or (lambda *args, **kwargs: FakeResponse()),
        env={
            "DEEPSEEK_API_KEY": "secret-test-key",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.test",
            "DEEPSEEK_MODEL": "deepseek-flash",
            "DEEPSEEK_THINKING_TYPE": "disabled",
            "WORKFLOW_DEEPSEEK_CALLS_PER_TASK": "1",
        },
    )


def create_task(workflow: AgentWorkflow) -> dict:
    return workflow.create_task(
        objective="Implement one feature",
        scope="Only the test file",
        allowed_paths=["src"],
        acceptance_criteria=["tests pass", "scope is respected"],
    )


def test_task_ids_are_unique(tmp_path: Path) -> None:
    workflow = make_workflow(tmp_path)
    first = create_task(workflow)
    second = create_task(workflow)
    assert first["task_id"] != second["task_id"]


def test_deepseek_is_called_exactly_once_after_success(tmp_path: Path) -> None:
    calls = []

    def post(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse()

    workflow = make_workflow(tmp_path, post=post)
    task = create_task(workflow)
    completed = workflow.execute_deepseek(task["task_id"])
    assert completed["status"] == "deepseek_completed"
    with pytest.raises(DuplicateExecutionError):
        workflow.execute_deepseek(task["task_id"])
    assert len(calls) == 1


def test_failed_call_is_consumed_and_secret_is_not_written(tmp_path: Path) -> None:
    calls = 0

    def post(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("network failed for secret-test-key")

    workflow = make_workflow(tmp_path, post=post)
    task = create_task(workflow)
    failed = workflow.execute_deepseek(task["task_id"])
    assert failed["status"] == "deepseek_failed"
    with pytest.raises(DuplicateExecutionError):
        workflow.execute_deepseek(task["task_id"])
    all_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "workflow" / "tasks" / task["task_id"]).rglob("*")
        if path.is_file()
    )
    assert calls == 1
    assert "secret-test-key" not in all_text
    assert "<redacted>" in all_text


def test_state_transitions_and_acceptance_require_all_criteria(tmp_path: Path) -> None:
    workflow = make_workflow(tmp_path)
    task = create_task(workflow)
    with pytest.raises(InvalidTransitionError):
        workflow.record_luna_review(
            task["task_id"], verdict="approved", notes="too early", changed_files=[]
        )
    workflow.execute_deepseek(task["task_id"])
    with pytest.raises(InvalidTransitionError):
        workflow.record_sol_decision(
            task["task_id"],
            decision="accepted",
            notes="too early",
            criterion_results={"tests pass": True, "scope is respected": True},
        )
    workflow.record_luna_review(
        task["task_id"], verdict="approved", notes="reviewed", changed_files=[]
    )
    with pytest.raises(WorkflowError):
        workflow.record_sol_decision(
            task["task_id"],
            decision="accepted",
            notes="one failed",
            criterion_results={"tests pass": False, "scope is respected": True},
        )
    accepted = workflow.record_sol_decision(
        task["task_id"],
        decision="accepted",
        notes="all checks pass",
        criterion_results={"tests pass": True, "scope is respected": True},
    )
    assert accepted["status"] == "sol_accepted"
    assert workflow.verify(task["task_id"])["ok"] is True


def test_corrected_review_hashes_files_and_detects_later_change(tmp_path: Path) -> None:
    workflow = make_workflow(tmp_path)
    task = create_task(workflow)
    workflow.execute_deepseek(task["task_id"])
    changed = tmp_path / "src" / "feature.py"
    changed.write_text("value = 1\n", encoding="utf-8")
    workflow.record_luna_review(
        task["task_id"],
        verdict="corrected",
        notes="fixed implementation",
        changed_files=["src/feature.py"],
    )
    assert workflow.verify(task["task_id"])["ok"] is True
    changed.write_text("value = 2\n", encoding="utf-8")
    with pytest.raises(AuditVerificationError, match="reviewed file changed"):
        workflow.verify(task["task_id"])


def test_corrected_review_requires_a_file(tmp_path: Path) -> None:
    workflow = make_workflow(tmp_path)
    task = create_task(workflow)
    workflow.execute_deepseek(task["task_id"])
    with pytest.raises(WorkflowError, match="at least one"):
        workflow.record_luna_review(
            task["task_id"], verdict="corrected", notes="claimed correction", changed_files=[]
        )


def test_revision_creates_linked_task_and_supersedes_parent(tmp_path: Path) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("offline")

    workflow = make_workflow(tmp_path, post=fail)
    parent = create_task(workflow)
    workflow.execute_deepseek(parent["task_id"])
    with pytest.raises(InvalidTransitionError, match="Sol rejection"):
        workflow.revise_task(parent["task_id"])
    workflow.record_luna_review(
        parent["task_id"],
        verdict="blocked",
        notes="DeepSeek call failed; there is no implementation to correct",
        changed_files=[],
    )
    workflow.record_sol_decision(
        parent["task_id"],
        decision="rejected",
        notes="execution failed",
        criterion_results={"tests pass": False, "scope is respected": False},
    )
    child = workflow.revise_task(parent["task_id"], objective="Clarified objective")
    assert child["parent_task_id"] == parent["task_id"]
    assert child["revision"] == 2
    assert workflow.show(parent["task_id"])["task"]["status"] == "superseded"
    assert workflow.show(parent["task_id"])["task"]["superseded_by"] == child["task_id"]


def test_failed_execution_still_requires_luna_and_sol_records(tmp_path: Path) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("offline")

    workflow = make_workflow(tmp_path, post=fail)
    task = create_task(workflow)
    workflow.execute_deepseek(task["task_id"])
    with pytest.raises(WorkflowError, match="must be recorded as blocked"):
        workflow.record_luna_review(
            task["task_id"], verdict="approved", notes="wrong", changed_files=[]
        )
    workflow.record_luna_review(
        task["task_id"], verdict="blocked", notes="no result", changed_files=[]
    )
    with pytest.raises(WorkflowError, match="Luna-blocked"):
        workflow.record_sol_decision(
            task["task_id"],
            decision="accepted",
            notes="wrong",
            criterion_results={"tests pass": True, "scope is respected": True},
        )
    rejected = workflow.record_sol_decision(
        task["task_id"],
        decision="rejected",
        notes="recorded failure",
        criterion_results={"tests pass": False, "scope is respected": False},
    )
    assert rejected["status"] == "sol_rejected"
    assert workflow.verify(task["task_id"])["ok"] is True


def test_event_tampering_is_detected(tmp_path: Path) -> None:
    workflow = make_workflow(tmp_path)
    task = create_task(workflow)
    events_path = tmp_path / "workflow" / "tasks" / task["task_id"] / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    events[0]["payload"]["scope"] = "tampered"
    events_path.write_text("\n".join(json.dumps(item) for item in events) + "\n", encoding="utf-8")
    with pytest.raises(AuditVerificationError, match="hash mismatch"):
        workflow.verify(task["task_id"])


def test_immutable_stage_artifact_cannot_be_replaced(tmp_path: Path) -> None:
    workflow = make_workflow(tmp_path)
    task = create_task(workflow)
    with pytest.raises(WorkflowError, match="immutable artifact"):
        workflow._record_artifact(task, "sol_plan.json", {"changed": True})


def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    workflow = make_workflow(tmp_path)
    with pytest.raises(PathViolationError):
        workflow.create_task(
            objective="bad path",
            scope="bad path",
            allowed_paths=["../outside"],
            acceptance_criteria=["blocked"],
        )


def test_doctor_is_offline_and_does_not_call_http(tmp_path: Path) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("doctor must not use the network")

    result = make_workflow(tmp_path, post=forbidden).doctor()
    assert result["ok"] is True
    assert result["network_request_made"] is False
