from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from pydantic import ValidationError

from captcha_verification.actions import plan_action
from captcha_verification.classification import classify
from captcha_verification.contracts import (
    ActionPlan,
    AuthorizationRecord,
    BusinessAcceptanceReceipt,
    ClassificationRequest,
    OperationStatus,
    PlanActionRequest,
    ResultEnvelope,
    SolveRequest,
    decide_promotion,
)
from captcha_verification.receipt_chain import run_local_e2e
from captcha_verification.solvers import solve
from captcha_verification.contracts.export import export_schemas
from captcha_verification.registries import DEFAULT_REGISTRY
from captcha_verification.services import ScaffoldSpec, build_scaffold, write_scaffold
from captcha_verification.agent_runtime import (
    AgentPolicyManifest,
    CodexAdapter,
    EvalRunner,
    IndependentReviewer,
    JobManifest,
    MockBackend,
    PromptPackInstaller,
    ProvenanceRecord,
    ProvenanceRegistry,
    evaluate_policy,
)
from captcha_verification.agent_runtime.dashboard import summarize


def _read_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def _print(envelope: ResultEnvelope) -> None:
    print(envelope.model_dump_json(indent=2))


def _request_id() -> str:
    return f"req_{uuid.uuid4().hex}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="captcha-skills", description="CAPTCHA Verification Skills core CLI")
    subcommands = parser.add_subparsers(dest="command", required=True)

    schema = subcommands.add_parser("export-schemas", help="Export canonical JSON Schemas")
    schema.add_argument("output", type=Path, nargs="?", default=Path("schemas/v1"))

    validate = subcommands.add_parser("validate", help="Validate a canonical contract")
    validate_sub = validate.add_subparsers(dest="contract", required=True)
    for name in ("authorization", "action", "business-receipt"):
        command = validate_sub.add_parser(name)
        command.add_argument("path", type=Path)

    registry = subcommands.add_parser("registry", help="Inspect the canonical registry")
    registry_sub = registry.add_subparsers(dest="registry_command", required=True)
    registry_list = registry_sub.add_parser("list")
    registry_list.add_argument("--type", choices=["solver", "model", "dataset", "action", "target"])
    registry_sub.add_parser("validate")

    promotion = subcommands.add_parser("evaluate", help="Evaluate first-party business acceptance receipts")
    promotion.add_argument("--authorization", type=Path, required=True)
    promotion.add_argument("--receipt", type=Path, action="append", required=True)
    promotion.add_argument("--repeat-required", type=int, default=2)

    for name in ("classify", "solve", "plan-action"):
        runtime = subcommands.add_parser(name, help=f"Run the local reference {name} operation")
        runtime.add_argument("--request", type=Path)

    e2e = subcommands.add_parser("e2e-local", help="Run the self-owned local first-party receipt chain")
    e2e.add_argument("--rounds", type=int, default=2)
    e2e.add_argument("--negative-matrix", choices=["all"], default="all")
    e2e.add_argument("--output", type=Path)

    scaffold = subcommands.add_parser("scaffold-target-adapter", help="Generate a private adapter engineering scaffold")
    scaffold.add_argument("--target-id", required=True)
    scaffold.add_argument("--challenge-family", required=True)
    scaffold.add_argument("--transport", dest="transports", action="append", choices=["cli", "fastapi", "mcp"], default=[])
    scaffold.add_argument("--output-root", type=Path)
    scaffold.add_argument("--template-root", type=Path)
    scaffold.add_argument("--write", action="store_true")

    runtime = subcommands.add_parser("runtime", help="Run controlled AI jobs")
    runtime_sub = runtime.add_subparsers(dest="runtime_command", required=True)
    inspect = runtime_sub.add_parser("inspect")
    inspect.add_argument("--job", type=Path, required=True)
    inspect.add_argument("--policy", type=Path, required=True)
    run_codex = runtime_sub.add_parser("run-codex")
    run_codex.add_argument("--job", type=Path, required=True)
    run_codex.add_argument("--policy", type=Path, required=True)
    run_codex.add_argument("--executable", default="codex")
    run_codex.add_argument("--workspace", type=Path)
    run_codex.add_argument("--prompt")
    run_codex.add_argument("--receipt", type=Path)

    prompts = subcommands.add_parser("prompts", help="Inspect and manage prompt packs")
    prompts_sub = prompts.add_subparsers(dest="prompts_command", required=True)
    for name in ("inspect", "dry-run", "apply"):
        command = prompts_sub.add_parser(name)
        command.add_argument("--source", type=Path, required=True)
        command.add_argument("--destination", type=Path, required=True)
        command.add_argument("--ledger", type=Path, required=True)
    rollback = prompts_sub.add_parser("rollback")
    rollback.add_argument("--backup-id", required=True)
    rollback.add_argument("--ledger", type=Path, required=True)

    evaluation = subcommands.add_parser("eval", help="Run offline boundary evaluations")
    evaluation_sub = evaluation.add_subparsers(dest="eval_command", required=True)
    eval_run = evaluation_sub.add_parser("run")
    eval_run.add_argument("--policy", type=Path, required=True)
    eval_run.add_argument("--model", default="mock-model")
    eval_run.add_argument("--effort", default="medium")
    eval_run.add_argument("--output", type=Path)

    review = subcommands.add_parser("review", help="Independently review a result")
    review_sub = review.add_subparsers(dest="review_command", required=True)
    review_result = review_sub.add_parser("result")
    review_result.add_argument("--result", type=Path, required=True)

    provenance = subcommands.add_parser("provenance", help="Inspect provenance")
    provenance_sub = provenance.add_subparsers(dest="provenance_command", required=True)
    provenance_verify = provenance_sub.add_parser("verify")
    provenance_verify.add_argument("--registry", type=Path, required=True)

    dashboard = subcommands.add_parser("dashboard", help="Read-only runtime dashboard")
    dashboard_sub = dashboard.add_subparsers(dest="dashboard_command", required=True)
    dashboard_summary = dashboard_sub.add_parser("summary")
    dashboard_summary.add_argument("--root", type=Path, required=True)

    return parser


def run(args: argparse.Namespace) -> int:
    request_id = _request_id()
    try:
        if args.command == "export-schemas":
            paths = export_schemas(args.output)
            _print(ResultEnvelope(operation_status=OperationStatus.SUCCEEDED, request_id=request_id, result={"paths": [str(path) for path in paths]}))
            return 0
        if args.command == "validate":
            models = {
                "authorization": AuthorizationRecord,
                "action": ActionPlan,
                "business-receipt": BusinessAcceptanceReceipt,
            }
            value = models[args.contract].model_validate(_read_json(args.path))
            _print(ResultEnvelope(operation_status=OperationStatus.SUCCEEDED, request_id=request_id, result={"contract": args.contract, "value": value.model_dump(mode="json")}))
            return 0
        if args.command == "registry":
            if args.registry_command == "list":
                entries = [entry.model_dump(mode="json") for entry in DEFAULT_REGISTRY.list(args.type)]
                _print(ResultEnvelope(operation_status=OperationStatus.SUCCEEDED, request_id=request_id, result={"entries": entries}))
                return 0
            errors = DEFAULT_REGISTRY.validate_imports()
            status = OperationStatus.SUCCEEDED if not errors else OperationStatus.FAILED
            _print(ResultEnvelope(operation_status=status, request_id=request_id, result={"errors": errors}))
            return 0 if not errors else 1
        if args.command == "evaluate":
            authorization = AuthorizationRecord.model_validate(_read_json(args.authorization))
            receipts = [BusinessAcceptanceReceipt.model_validate(_read_json(path)) for path in args.receipt]
            decision = decide_promotion(authorization=authorization, receipts=receipts, repeat_required=args.repeat_required)
            status = OperationStatus.SUCCEEDED if decision.status == "approved" else OperationStatus.BLOCKED
            _print(ResultEnvelope(operation_status=status, request_id=request_id, result=decision.model_dump(mode="json"), missing_evidence=decision.blockers))
            return 0 if decision.status == "approved" else 3
        if args.command == "scaffold-target-adapter":
            package_root = Path(__file__).resolve().parent
            template_root = args.template_root or package_root / "templates" / "target-adapter"
            output_root = args.output_root or Path("private") / "targets" / args.target_id
            spec = ScaffoldSpec(
                target_id=args.target_id,
                challenge_family=args.challenge_family,
                transports=args.transports or ["cli"],
            )
            scaffold = build_scaffold(spec, template_root=template_root, output_root=output_root)
            result = scaffold.as_dict()
            result["write_mode"] = bool(args.write)
            result["written_paths"] = [str(path) for path in write_scaffold(scaffold)] if args.write else []
            _print(
                ResultEnvelope(
                    operation_status=OperationStatus.SUCCEEDED,
                    request_id=request_id,
                    result=result,
                    warnings=[] if args.write else ["dry-run only; no files were written"],
                    missing_evidence=list(scaffold.missing_evidence),
                )
            )
            return 0
        if args.command == "runtime":
            job = JobManifest.model_validate(_read_json(args.job))
            policy = AgentPolicyManifest.model_validate(_read_json(args.policy))
            decision = evaluate_policy(job, policy)
            _print(ResultEnvelope(operation_status=OperationStatus.SUCCEEDED if decision.allowed else OperationStatus.BLOCKED, request_id=request_id, result=decision.model_dump(mode="json"), missing_evidence=decision.denied_reasons))
            if args.runtime_command == "inspect":
                return 0 if decision.allowed else 4
            result = CodexAdapter(args.executable).run(job, policy, workspace=args.workspace, prompt=args.prompt, receipt_path=args.receipt)
            status = OperationStatus.SUCCEEDED if result.status == "completed" else OperationStatus.BLOCKED if result.status == "blocked" else OperationStatus.FAILED
            _print(ResultEnvelope(operation_status=status, request_id=request_id, result=result.model_dump(mode="json"), missing_evidence=result.missing_evidence))
            return 0 if result.status == "completed" else 4
        if args.command == "prompts":
            installer = PromptPackInstaller(allowed_destination_roots=(args.destination.parent if hasattr(args, "destination") else args.ledger.parent,), ledger_path=args.ledger)
            if args.prompts_command == "rollback":
                _print(ResultEnvelope(operation_status=OperationStatus.SUCCEEDED, request_id=request_id, result=installer.rollback(args.backup_id)))
                return 0
            plan = installer.inspect(args.source, args.destination)
            if args.prompts_command == "inspect":
                _print(ResultEnvelope(operation_status=OperationStatus.SUCCEEDED, request_id=request_id, result=plan.to_dict()))
                return 0
            if args.prompts_command == "dry-run":
                _print(ResultEnvelope(operation_status=OperationStatus.SUCCEEDED, request_id=request_id, result=installer.dry_run(plan)))
                return 0
            result = installer.apply(plan)
            status = OperationStatus.SUCCEEDED if result.get("status") == "applied" else OperationStatus.BLOCKED
            _print(ResultEnvelope(operation_status=status, request_id=request_id, result=result))
            return 0 if status == OperationStatus.SUCCEEDED else 4
        if args.command == "eval" and args.eval_command == "run":
            policy = AgentPolicyManifest.model_validate(_read_json(args.policy))
            run_result = EvalRunner(MockBackend(), policy).run(model=args.model, effort=args.effort)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(run_result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            status = OperationStatus.SUCCEEDED if all(item.passed for item in run_result.results) else OperationStatus.BLOCKED
            _print(ResultEnvelope(operation_status=status, request_id=request_id, result=run_result.to_dict()))
            return 0 if status == OperationStatus.SUCCEEDED else 4
        if args.command == "review" and args.review_command == "result":
            result = ResultManifest.model_validate(_read_json(args.result))
            verdict = IndependentReviewer().review(result)
            status = OperationStatus.SUCCEEDED if verdict.verdict == "accepted" else OperationStatus.BLOCKED
            _print(ResultEnvelope(operation_status=status, request_id=request_id, result=verdict.model_dump(mode="json"), missing_evidence=verdict.missing_evidence))
            return 0 if status == OperationStatus.SUCCEEDED else 4
        if args.command == "provenance" and args.provenance_command == "verify":
            registry = ProvenanceRegistry.load(args.registry)
            errors = registry.verify()
            status = OperationStatus.SUCCEEDED if not errors else OperationStatus.FAILED
            _print(ResultEnvelope(operation_status=status, request_id=request_id, result={"errors": errors, "registry": registry.to_dict()}))
            return 0 if not errors else 1
        if args.command == "dashboard" and args.dashboard_command == "summary":
            _print(ResultEnvelope(operation_status=OperationStatus.SUCCEEDED, request_id=request_id, result=summarize(args.root)))
            return 0
        if args.command in {"classify", "solve", "plan-action"} and args.request is None:
            _print(ResultEnvelope(operation_status=OperationStatus.BLOCKED, request_id=request_id, result={"command": args.command}, missing_evidence=["local fixture request file is required"]))
            return 4
        if args.command == "classify":
            value = classify(ClassificationRequest.model_validate(_read_json(args.request)))
            _print(ResultEnvelope(operation_status=OperationStatus.SUCCEEDED, request_id=request_id, result=value.model_dump(mode="json"), warnings=value.warnings))
            return 0
        if args.command == "solve":
            value = solve(SolveRequest.model_validate(_read_json(args.request)))
            status = OperationStatus.SUCCEEDED if value.status == "produced" else OperationStatus.BLOCKED
            _print(ResultEnvelope(operation_status=status, request_id=request_id, result=value.model_dump(mode="json"), warnings=value.warnings))
            return 0 if value.status == "produced" else 4
        if args.command == "plan-action":
            value = plan_action(PlanActionRequest.model_validate(_read_json(args.request)))
            _print(ResultEnvelope(operation_status=OperationStatus.SUCCEEDED, request_id=request_id, result=value.model_dump(mode="json")))
            return 0
        if args.command == "e2e-local":
            if args.rounds < 2:
                raise ValueError("--rounds must be at least 2 to verify a fresh repeat")
            value = run_local_e2e(rounds=args.rounds)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            approved = value["promotion_decision"]["status"] == "approved" and value["negative_control_ledger_delta"] == 0
            status = OperationStatus.SUCCEEDED if approved else OperationStatus.BLOCKED
            _print(ResultEnvelope(operation_status=status, request_id=request_id, result=value))
            return 0 if approved else 4
        _print(ResultEnvelope(operation_status=OperationStatus.BLOCKED, request_id=request_id, result={"command": args.command}, missing_evidence=["command implementation is not available"]))
        return 4
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        _print(ResultEnvelope(operation_status=OperationStatus.FAILED, request_id=request_id, errors=[{"code": "validation_error", "message": str(exc)}]))
        return 1


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
