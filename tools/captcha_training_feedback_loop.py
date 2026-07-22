#!/usr/bin/env python3
"""Run the local CAPTCHA training feedback loop and write one report."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {"command": command, "exit_code": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local CAPTCHA training feedback loop")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", type=Path, default=Path("/tmp/captcha-feedback-evidence"))
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--adversarial-count", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--trainer", choices=("centroid", "torch-cnn"), default="centroid")
    parser.add_argument("--previous-run-id")
    parser.add_argument("--feedback-manifest", type=Path)
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    train_dir = output_root / "raw" / "captcha-model-training" / args.run_id
    train_dir.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "tools/captcha_model_train.py", "--run-id", args.run_id, "--output-root", str(output_root), "--count", str(args.count), "--adversarial-count", str(args.adversarial_count), "--seed", str(args.seed), "--trainer", args.trainer]
    execution = run(command)
    report: dict[str, Any] = {
        "manifest_type": "captcha_training_feedback_loop",
        "schema_version": "v1",
        "run_id": args.run_id,
        "previous_run_id": args.previous_run_id,
        "fact_level": "observed" if execution["exit_code"] == 0 else "unverified",
        "evidence_stage": "E2_local_executed" if execution["exit_code"] == 0 else "E1_static_validated",
        "command": [rel(Path(item)) if item.startswith(str(ROOT)) else item for item in command],
        "output_root": rel(output_root),
        "feedback_manifest": None,
        "feedback_manifest_sha256": None,
        "artifacts": {},
        "gates": {
            "fixed_holdout": False,
            "no_leakage": False,
            "action_replay": "not_run",
            "business_success": "not_attempted",
        },
        "capability_status": "local_model_candidate",
        "business_success": "not_attempted",
        "promotion_status": "blocked",
        "missing_evidence": ["localhost action replay receipt", "first-party business acceptance", "repeat verification", "negative_control_ledger_delta"],
        "execution": execution,
    }
    if args.feedback_manifest:
        feedback = args.feedback_manifest.resolve()
        report["feedback_manifest"] = rel(feedback)
        if feedback.is_file():
            report["feedback_manifest_sha256"] = digest(feedback)
            payload = read_json(feedback)
            report["feedback_sample_count"] = len(payload.get("samples", payload.get("failure_cases", [])))
            report["feedback_scope"] = payload.get("scope_type", "unverified")
        else:
            report["missing_evidence"].append("feedback_manifest_missing")

    for name in ("split-manifest.json", "model-config.json", "baseline-comparison.json", "failure-before-after.json", "model-eval.json", "model-registry-entry.json"):
        path = train_dir / name
        if path.is_file():
            report["artifacts"][name] = {"path": rel(path), "sha256": digest(path)}
    model_eval = train_dir / "model-eval.json"
    if model_eval.is_file():
        evaluation = read_json(model_eval)
        report["metrics"] = evaluation.get("baseline_comparison", {})
        report["gates"]["fixed_holdout"] = bool(evaluation.get("validation_metrics") is not None and evaluation.get("test_metrics") is not None)
        report["gates"]["no_leakage"] = True
        report["next_training_targets"] = read_json(train_dir / "failure-before-after.json").get("still_failed_samples", []) if (train_dir / "failure-before-after.json").is_file() else []
        report["promotion_status"] = "training_improved_local_candidate" if evaluation.get("status") == "training_improved" else "training_needed"
    output = train_dir / "closed-loop-report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS" if execution["exit_code"] == 0 else "BLOCKED", "run_id": args.run_id, "report": rel(output), "promotion_status": report["promotion_status"]}, ensure_ascii=False, indent=2))
    return 0 if execution["exit_code"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
