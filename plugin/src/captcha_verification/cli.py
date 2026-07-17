from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from pydantic import ValidationError

from captcha_verification.contracts import (
    ActionPlan,
    AuthorizationRecord,
    BusinessAcceptanceReceipt,
    OperationStatus,
    ResultEnvelope,
    decide_promotion,
)
from captcha_verification.contracts.export import export_schemas
from captcha_verification.registries import DEFAULT_REGISTRY
from captcha_verification.services import ScaffoldSpec, build_scaffold, write_scaffold


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
        placeholder = subcommands.add_parser(name)
        placeholder.add_argument("arguments", nargs=argparse.REMAINDER)

    scaffold = subcommands.add_parser("scaffold-target-adapter", help="Generate a private adapter engineering scaffold")
    scaffold.add_argument("--target-id", required=True)
    scaffold.add_argument("--challenge-family", required=True)
    scaffold.add_argument("--transport", dest="transports", action="append", choices=["cli", "fastapi", "mcp"], default=[])
    scaffold.add_argument("--output-root", type=Path)
    scaffold.add_argument("--template-root", type=Path)
    scaffold.add_argument("--write", action="store_true")

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
        _print(ResultEnvelope(operation_status=OperationStatus.BLOCKED, request_id=request_id, result={"command": args.command}, missing_evidence=["command implementation is not available in this release candidate"]))
        return 4
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        _print(ResultEnvelope(operation_status=OperationStatus.FAILED, request_id=request_id, errors=[{"code": "validation_error", "message": str(exc)}]))
        return 1


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
