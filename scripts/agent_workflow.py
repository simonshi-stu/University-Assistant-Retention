"""Command-line interface for the auditable Sol/DeepSeek/Luna workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from course_retention.agent_workflow import AgentWorkflow, WorkflowError  # noqa: E402


def _criterion_result(value: str) -> tuple[str, bool]:
    try:
        criterion, result = value.rsplit("::", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use 'criterion text::pass' or '::fail'") from exc
    normalized = result.strip().lower()
    if not criterion.strip() or normalized not in {"pass", "fail"}:
        raise argparse.ArgumentTypeError("use 'criterion text::pass' or '::fail'")
    return criterion.strip(), normalized == "pass"


def _add_create_fields(parser: argparse.ArgumentParser, *, optional: bool = False) -> None:
    requirement: dict[str, Any] = {"required": not optional}
    parser.add_argument("--objective", **requirement)
    parser.add_argument("--scope", **requirement)
    parser.add_argument("--allowed-path", action="append", dest="allowed_paths", **requirement)
    parser.add_argument("--criterion", action="append", dest="criteria", **requirement)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auditable one-call DeepSeek development workflow"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="create a Sol-planned task")
    _add_create_fields(create)

    execute = subparsers.add_parser("execute", help="make the task's one DeepSeek call")
    execute.add_argument("task_id")

    review = subparsers.add_parser("review", help="record Luna review/corrections")
    review.add_argument("task_id")
    review.add_argument(
        "--verdict", choices=("approved", "corrected", "blocked"), required=True
    )
    review.add_argument("--notes", required=True)
    review.add_argument("--changed-file", action="append", default=[])

    accept = subparsers.add_parser("accept", help="record Sol's final decision")
    accept.add_argument("task_id")
    accept.add_argument("--decision", choices=("accepted", "rejected"), required=True)
    accept.add_argument("--notes", required=True)
    accept.add_argument("--result", action="append", type=_criterion_result, required=True)

    revise = subparsers.add_parser("revise", help="create a new task from a failed one")
    revise.add_argument("task_id")
    _add_create_fields(revise, optional=True)

    for name in ("show", "verify"):
        command = subparsers.add_parser(name)
        command.add_argument("task_id")
    subparsers.add_parser("doctor", help="check local configuration without network access")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workflow = AgentWorkflow(REPO_ROOT)
    try:
        if args.command == "create":
            result = workflow.create_task(
                objective=args.objective,
                scope=args.scope,
                allowed_paths=args.allowed_paths,
                acceptance_criteria=args.criteria,
            )
        elif args.command == "execute":
            result = workflow.execute_deepseek(args.task_id)
        elif args.command == "review":
            result = workflow.record_luna_review(
                args.task_id,
                verdict=args.verdict,
                notes=args.notes,
                changed_files=args.changed_file,
            )
        elif args.command == "accept":
            criterion_results = dict(args.result)
            if len(criterion_results) != len(args.result):
                raise WorkflowError("each acceptance criterion result must be unique")
            result = workflow.record_sol_decision(
                args.task_id,
                decision=args.decision,
                notes=args.notes,
                criterion_results=criterion_results,
            )
        elif args.command == "revise":
            result = workflow.revise_task(
                args.task_id,
                objective=args.objective,
                scope=args.scope,
                allowed_paths=args.allowed_paths,
                acceptance_criteria=args.criteria,
            )
        elif args.command == "show":
            result = workflow.show(args.task_id)
        elif args.command == "verify":
            result = workflow.verify(args.task_id)
        else:
            result = workflow.doctor()
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result.get("ok", True) else 1
    except WorkflowError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
