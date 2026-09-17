"""Auditable three-role workflow for repository development tasks.

This module is development tooling.  The analytics pipeline never imports or
calls it at runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import requests


SOL = "gpt-5.6-sol"
LUNA = "gpt-5.6-luna"
DEEPSEEK = "deepseek-v4.1-flash"

PLANNED = "planned"
DEEPSEEK_COMPLETED = "deepseek_completed"
DEEPSEEK_FAILED = "deepseek_failed"
LUNA_REVIEWED = "luna_reviewed"
SOL_ACCEPTED = "sol_accepted"
SOL_REJECTED = "sol_rejected"
SUPERSEDED = "superseded"

TASK_ID_PATTERN = re.compile(r"^CRP-\d{8}-\d{6}-[0-9A-F]{8}$")
ZERO_HASH = "0" * 64


class WorkflowError(RuntimeError):
    """Base workflow error."""


class InvalidTransitionError(WorkflowError):
    """Raised when a role attempts an invalid state transition."""


class DuplicateExecutionError(WorkflowError):
    """Raised when DeepSeek would be invoked more than once for one task."""


class AuditVerificationError(WorkflowError):
    """Raised when an audit artifact or hash chain has been altered."""


class PathViolationError(WorkflowError):
    """Raised when a path leaves the repository or the task allowlist."""


def canonical_json(value: Any) -> str:
    """Return deterministic JSON used by the event hash chain."""

    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_dotenv(path: Path) -> dict[str, str]:
    """Read simple KEY=value entries without mutating or logging the environment."""

    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value[:1] in {"'", '"'}:
            value = value[1:-1]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            values[key] = value
    return values


def new_task_id(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    return f"CRP-{moment.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(4).upper()}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(payload) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _exclusive_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(payload) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise WorkflowError(f"immutable artifact already exists: {path}") from exc


class AgentWorkflow:
    """Persist and enforce the Sol -> DeepSeek -> Luna -> Sol workflow."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        http_post: Callable[..., Any] | None = None,
        env: Mapping[str, str] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.tasks_root = self.repo_root / "workflow" / "tasks"
        self.http_post = http_post or requests.post
        self.env_override = dict(env) if env is not None else None
        self.id_factory = id_factory or new_task_id

    def _environment(self) -> dict[str, str]:
        if self.env_override is not None:
            return dict(self.env_override)
        values = load_dotenv(self.repo_root / ".env")
        values.update(os.environ)
        return values

    def _task_dir(self, task_id: str) -> Path:
        if not TASK_ID_PATTERN.fullmatch(task_id):
            raise WorkflowError(f"invalid task id: {task_id}")
        return self.tasks_root / task_id

    def _load_task(self, task_id: str) -> dict[str, Any]:
        path = self._task_dir(task_id) / "task.json"
        if not path.is_file():
            raise WorkflowError(f"unknown task: {task_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_task(self, task: Mapping[str, Any]) -> None:
        _atomic_json(self._task_dir(str(task["task_id"])) / "task.json", task)

    def _safe_relative(self, candidate: str | Path) -> str:
        path = Path(candidate)
        if path.is_absolute() or ".." in path.parts:
            raise PathViolationError(f"path must be repository-relative: {candidate}")
        resolved = (self.repo_root / path).resolve()
        try:
            relative = resolved.relative_to(self.repo_root)
        except ValueError as exc:
            raise PathViolationError(f"path leaves repository: {candidate}") from exc
        if not relative.parts:
            raise PathViolationError("repository root is not an allowed file path")
        return relative.as_posix()

    @staticmethod
    def _path_allowed(path: str, allowed_paths: Sequence[str]) -> bool:
        candidate = Path(path)
        for allowed in allowed_paths:
            root = Path(allowed)
            if candidate == root or root in candidate.parents:
                return True
        return False

    def _events(self, task_id: str) -> list[dict[str, Any]]:
        path = self._task_dir(task_id) / "events.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def _append_event(
        self, task_id: str, *, actor: str, action: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        events = self._events(task_id)
        event = {
            "sequence": len(events) + 1,
            "timestamp_utc": _utc_now(),
            "actor": actor,
            "action": action,
            "payload": dict(payload),
            "prev_hash": events[-1]["event_hash"] if events else ZERO_HASH,
        }
        event["event_hash"] = sha256_bytes(canonical_json(event).encode("utf-8"))
        event_path = self._task_dir(task_id) / "events.jsonl"
        with event_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def _record_artifact(
        self, task: dict[str, Any], filename: str, payload: Mapping[str, Any]
    ) -> Path:
        path = self._task_dir(task["task_id"]) / "stages" / filename
        _exclusive_json(path, payload)
        relative = path.relative_to(self.repo_root).as_posix()
        task.setdefault("artifacts", {})[filename] = {
            "path": relative,
            "sha256": sha256_file(path),
        }
        return path

    def create_task(
        self,
        *,
        objective: str,
        scope: str,
        allowed_paths: Sequence[str],
        acceptance_criteria: Sequence[str],
        parent_task_id: str | None = None,
        revision: int = 1,
    ) -> dict[str, Any]:
        if not objective.strip() or not scope.strip():
            raise WorkflowError("objective and scope are required")
        if not allowed_paths or not acceptance_criteria:
            raise WorkflowError("allowed paths and acceptance criteria are required")
        normalized_paths = [self._safe_relative(path) for path in allowed_paths]
        criteria = [criterion.strip() for criterion in acceptance_criteria if criterion.strip()]
        if len(criteria) != len(acceptance_criteria):
            raise WorkflowError("acceptance criteria cannot be empty")
        if len(set(criteria)) != len(criteria):
            raise WorkflowError("acceptance criteria must be unique")
        if parent_task_id is not None:
            self._load_task(parent_task_id)

        task_id = self.id_factory()
        if not TASK_ID_PATTERN.fullmatch(task_id):
            raise WorkflowError(f"id factory returned invalid task id: {task_id}")
        directory = self._task_dir(task_id)
        directory.mkdir(parents=True, exist_ok=False)
        task: dict[str, Any] = {
            "task_id": task_id,
            "parent_task_id": parent_task_id,
            "revision": revision,
            "objective": objective.strip(),
            "scope": scope.strip(),
            "allowed_paths": normalized_paths,
            "acceptance_criteria": criteria,
            "status": PLANNED,
            "deepseek_attempts": 0,
            "created_utc": _utc_now(),
            "updated_utc": _utc_now(),
            "artifacts": {},
        }
        plan = {
            "task_id": task_id,
            "actor": SOL,
            "objective": task["objective"],
            "scope": task["scope"],
            "allowed_paths": normalized_paths,
            "acceptance_criteria": criteria,
            "parent_task_id": parent_task_id,
            "revision": revision,
        }
        self._record_artifact(task, "sol_plan.json", plan)
        self._append_event(task_id, actor=SOL, action="planned", payload=plan)
        self._save_task(task)
        return task

    @staticmethod
    def _deepseek_prompt(task: Mapping[str, Any]) -> str:
        allowed = "\n".join(f"- {path}" for path in task["allowed_paths"])
        criteria = "\n".join(f"- {item}" for item in task["acceptance_criteria"])
        return (
            f"Task ID: {task['task_id']}\n"
            "You are the one-time DeepSeek implementation executor.\n\n"
            f"Objective:\n{task['objective']}\n\n"
            f"Scope:\n{task['scope']}\n\n"
            f"Allowed repository paths:\n{allowed}\n\n"
            f"Acceptance criteria:\n{criteria}\n\n"
            "Return a concise design followed by a complete unified diff. "
            "Do not touch paths outside the allowlist and do not claim unrun tests."
        )

    def execute_deepseek(self, task_id: str) -> dict[str, Any]:
        task = self._load_task(task_id)
        request_path = self._task_dir(task_id) / "stages" / "deepseek_request.json"
        if (
            task["status"] != PLANNED
            or task["deepseek_attempts"] != 0
            or request_path.exists()
        ):
            raise DuplicateExecutionError(f"DeepSeek already executed or reserved for {task_id}")

        environment = self._environment()
        api_key = environment.get("DEEPSEEK_API_KEY", "").strip()
        base_url = environment.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        model = environment.get("DEEPSEEK_MODEL", "deepseek-flash").strip()
        if not api_key or not model:
            raise WorkflowError("DeepSeek API key and model must be configured before execution")
        try:
            timeout = int(environment.get("DEEPSEEK_TIMEOUT_SECONDS", "180"))
        except ValueError as exc:
            raise WorkflowError("DEEPSEEK_TIMEOUT_SECONDS must be an integer") from exc

        prompt = self._deepseek_prompt(task)
        thinking_type = environment.get("DEEPSEEK_THINKING_TYPE", "disabled").strip()
        if thinking_type not in {"enabled", "disabled"}:
            raise WorkflowError("DEEPSEEK_THINKING_TYPE must be enabled or disabled")
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Return repository-ready code; never expose secrets."},
                {"role": "user", "content": prompt},
            ],
            "thinking": {"type": thinking_type},
            "stream": False,
        }
        request_record = {
            "task_id": task_id,
            "actor": DEEPSEEK,
            "url": f"{base_url}/chat/completions",
            "method": "POST",
            "model": model,
            "thinking_type": thinking_type,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "prompt": prompt,
            "attempt": 1,
            "automatic_retries": 0,
        }
        self._record_artifact(task, "deepseek_request.json", request_record)
        task["deepseek_attempts"] = 1
        task["updated_utc"] = _utc_now()
        self._append_event(
            task_id,
            actor=DEEPSEEK,
            action="deepseek_reserved",
            payload={"attempt": 1, "model": model, "prompt_sha256": request_record["prompt_sha256"]},
        )
        self._save_task(task)

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            response = self.http_post(
                request_record["url"], headers=headers, json=body, timeout=timeout
            )
            response.raise_for_status()
            raw = response.json()
            message = raw["choices"][0]["message"]
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise WorkflowError("DeepSeek returned no final visible content")
            response_record = {
                "task_id": task_id,
                "actor": DEEPSEEK,
                "model": raw.get("model", model),
                "response_id": raw.get("id"),
                "content": content,
                "content_sha256": sha256_bytes(content.encode("utf-8")),
                "usage": raw.get("usage", {}),
            }
            self._record_artifact(task, "deepseek_response.json", response_record)
            task["status"] = DEEPSEEK_COMPLETED
            self._append_event(
                task_id,
                actor=DEEPSEEK,
                action="deepseek_completed",
                payload={"content_sha256": response_record["content_sha256"]},
            )
        except Exception as exc:  # one attempt is consumed for every API/protocol failure
            safe_message = str(exc).replace(api_key, "<redacted>")
            failure_record = {
                "task_id": task_id,
                "actor": DEEPSEEK,
                "error_type": type(exc).__name__,
                "error": safe_message,
                "attempt_consumed": True,
            }
            self._record_artifact(task, "deepseek_failure.json", failure_record)
            task["status"] = DEEPSEEK_FAILED
            self._append_event(
                task_id,
                actor=DEEPSEEK,
                action="deepseek_failed",
                payload={"error_type": type(exc).__name__, "attempt_consumed": True},
            )
        task["updated_utc"] = _utc_now()
        self._save_task(task)
        return task

    def record_luna_review(
        self,
        task_id: str,
        *,
        verdict: str,
        notes: str,
        changed_files: Sequence[str],
    ) -> dict[str, Any]:
        task = self._load_task(task_id)
        if task["status"] not in {DEEPSEEK_COMPLETED, DEEPSEEK_FAILED}:
            raise InvalidTransitionError("Luna review requires one consumed DeepSeek execution")
        if verdict not in {"approved", "corrected", "blocked"}:
            raise WorkflowError("Luna verdict must be approved, corrected, or blocked")
        if task["status"] == DEEPSEEK_FAILED and verdict != "blocked":
            raise WorkflowError("a failed DeepSeek execution must be recorded as blocked")
        if verdict == "corrected" and not changed_files:
            raise WorkflowError("a corrected Luna review must record at least one changed file")
        if verdict == "blocked" and changed_files:
            raise WorkflowError("a blocked Luna review cannot claim changed files")
        file_records: list[dict[str, Any]] = []
        for candidate in changed_files:
            relative = self._safe_relative(candidate)
            if not self._path_allowed(relative, task["allowed_paths"]):
                raise PathViolationError(f"reviewed file is outside the task allowlist: {relative}")
            path = self.repo_root / relative
            if not path.is_file():
                raise WorkflowError(f"reviewed file does not exist: {relative}")
            file_records.append(
                {"path": relative, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
            )
        review = {
            "task_id": task_id,
            "actor": LUNA,
            "verdict": verdict,
            "notes": notes,
            "changed_files": file_records,
        }
        self._record_artifact(task, "luna_review.json", review)
        task["status"] = LUNA_REVIEWED
        task["updated_utc"] = _utc_now()
        self._append_event(
            task_id,
            actor=LUNA,
            action="luna_reviewed",
            payload={"verdict": verdict, "changed_files": file_records},
        )
        self._save_task(task)
        return task

    def record_sol_decision(
        self,
        task_id: str,
        *,
        decision: str,
        notes: str,
        criterion_results: Mapping[str, bool],
    ) -> dict[str, Any]:
        task = self._load_task(task_id)
        if task["status"] != LUNA_REVIEWED:
            raise InvalidTransitionError("Sol decision requires a completed Luna review")
        if decision not in {"accepted", "rejected"}:
            raise WorkflowError("Sol decision must be accepted or rejected")
        review_path = self._task_dir(task_id) / "stages" / "luna_review.json"
        review = json.loads(review_path.read_text(encoding="utf-8"))
        if decision == "accepted" and review["verdict"] == "blocked":
            raise WorkflowError("Sol cannot accept a Luna-blocked task")
        expected = set(task["acceptance_criteria"])
        if set(criterion_results) != expected:
            raise WorkflowError("criterion results must match every acceptance criterion exactly")
        if decision == "accepted" and not all(criterion_results.values()):
            raise WorkflowError("Sol cannot accept while an acceptance criterion fails")
        acceptance = {
            "task_id": task_id,
            "actor": SOL,
            "decision": decision,
            "notes": notes,
            "criterion_results": dict(criterion_results),
        }
        self._record_artifact(task, "sol_acceptance.json", acceptance)
        task["status"] = SOL_ACCEPTED if decision == "accepted" else SOL_REJECTED
        task["updated_utc"] = _utc_now()
        self._append_event(
            task_id,
            actor=SOL,
            action=task["status"],
            payload={"decision": decision, "criterion_results": dict(criterion_results)},
        )
        self._save_task(task)
        return task

    def revise_task(
        self,
        task_id: str,
        *,
        objective: str | None = None,
        scope: str | None = None,
        allowed_paths: Sequence[str] | None = None,
        acceptance_criteria: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        parent = self._load_task(task_id)
        if parent["status"] != SOL_REJECTED:
            raise InvalidTransitionError("a revision requires a recorded Sol rejection")
        child = self.create_task(
            objective=objective or parent["objective"],
            scope=scope or parent["scope"],
            allowed_paths=allowed_paths or parent["allowed_paths"],
            acceptance_criteria=acceptance_criteria or parent["acceptance_criteria"],
            parent_task_id=task_id,
            revision=int(parent["revision"]) + 1,
        )
        parent["status"] = SUPERSEDED
        parent["superseded_by"] = child["task_id"]
        parent["updated_utc"] = _utc_now()
        self._append_event(
            task_id,
            actor=SOL,
            action="superseded",
            payload={"superseded_by": child["task_id"]},
        )
        self._save_task(parent)
        return child

    def show(self, task_id: str) -> dict[str, Any]:
        return {"task": self._load_task(task_id), "events": self._events(task_id)}

    def verify(self, task_id: str) -> dict[str, Any]:
        task = self._load_task(task_id)
        events = self._events(task_id)
        if not events:
            raise AuditVerificationError("event log is empty")
        previous = ZERO_HASH
        attempts = 0
        derived_status = PLANNED
        state_actions = {
            "deepseek_completed": DEEPSEEK_COMPLETED,
            "deepseek_failed": DEEPSEEK_FAILED,
            "luna_reviewed": LUNA_REVIEWED,
            "sol_accepted": SOL_ACCEPTED,
            "sol_rejected": SOL_REJECTED,
            "superseded": SUPERSEDED,
        }
        for expected_sequence, stored in enumerate(events, start=1):
            if stored.get("sequence") != expected_sequence:
                raise AuditVerificationError("event sequence is not contiguous")
            if stored.get("prev_hash") != previous:
                raise AuditVerificationError("event previous hash does not match")
            event = dict(stored)
            claimed_hash = event.pop("event_hash", None)
            actual_hash = sha256_bytes(canonical_json(event).encode("utf-8"))
            if claimed_hash != actual_hash:
                raise AuditVerificationError("event hash mismatch")
            previous = str(claimed_hash)
            action = str(stored.get("action"))
            if action == "deepseek_reserved":
                attempts += 1
            if action in state_actions:
                derived_status = state_actions[action]
        if attempts != task["deepseek_attempts"] or attempts > 1:
            raise AuditVerificationError("DeepSeek attempt projection does not match audit log")
        if derived_status != task["status"]:
            raise AuditVerificationError("task state projection does not match audit log")
        for name, record in task.get("artifacts", {}).items():
            path = (self.repo_root / record["path"]).resolve()
            try:
                path.relative_to(self.repo_root)
            except ValueError as exc:
                raise AuditVerificationError(f"artifact path leaves repository: {name}") from exc
            if not path.is_file() or sha256_file(path) != record["sha256"]:
                raise AuditVerificationError(f"artifact hash mismatch: {name}")
        review_path = self._task_dir(task_id) / "stages" / "luna_review.json"
        if review_path.is_file():
            review = json.loads(review_path.read_text(encoding="utf-8"))
            for record in review["changed_files"]:
                path = self.repo_root / record["path"]
                if not path.is_file() or sha256_file(path) != record["sha256"]:
                    raise AuditVerificationError(f"reviewed file changed: {record['path']}")
        return {
            "ok": True,
            "task_id": task_id,
            "status": task["status"],
            "events": len(events),
            "deepseek_attempts": attempts,
            "head_hash": previous,
        }

    def doctor(self) -> dict[str, Any]:
        environment = self._environment()
        checks = {
            "repository_exists": self.repo_root.is_dir(),
            "deepseek_api_key_present": bool(environment.get("DEEPSEEK_API_KEY", "").strip()),
            "deepseek_base_url_present": bool(environment.get("DEEPSEEK_BASE_URL", "").strip()),
            "deepseek_model_present": bool(environment.get("DEEPSEEK_MODEL", "").strip()),
            "one_call_policy": environment.get("WORKFLOW_DEEPSEEK_CALLS_PER_TASK", "1") == "1",
        }
        return {
            "ok": all(checks.values()),
            "checks": checks,
            "models": {
                "supervisor": environment.get("WORKFLOW_SUPERVISOR_MODEL", SOL),
                "reviewer": environment.get("WORKFLOW_REVIEWER_MODEL", LUNA),
                "executor": environment.get("WORKFLOW_EXECUTOR_MODEL", DEEPSEEK),
            },
            "network_request_made": False,
        }
