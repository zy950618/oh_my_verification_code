#!/usr/bin/env python3
"""Audit CAPTCHA runs for answer leakage and split contamination."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
ACTION_ALLOWED_SOURCES = {
    "challenge_image",
    "challenge_image_screenshot",
    "challenge_image_crop",
    "master_image",
    "thumb_image",
    "instruction_text",
    "allowed_actions_schema",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def audit_predictions(path: Path, label: str) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    if not path.is_file():
        return violations
    payload = read_json(path)
    for item in payload.get("predictions", []):
        sample_id = item.get("sample_id")
        for key, reason in (
            ("label_read_for_prediction", "solver read label_path"),
            ("metadata_answer_read_for_prediction", "solver read metadata answer"),
            ("dom_read_for_prediction", "solver read DOM answer"),
            ("query_param_read_for_prediction", "solver read query expected"),
        ):
            if item.get(key) is not False:
                violations.append({"source": label, "sample_id": sample_id, "field": key, "reason": reason})
        sources = set(item.get("solver_input_sources") or [])
        if sources - {"challenge_image", "challenge_image_screenshot"}:
            violations.append({"source": label, "sample_id": sample_id, "field": "solver_input_sources", "reason": f"unexpected sources {sorted(sources)}"})
    return violations


def split_contamination(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    seen_images: dict[str, str] = {}
    seen_lineages: dict[str, str] = {}
    violations = []
    for sample in manifest.get("samples", []):
        image_path = str(sample.get("image_path"))
        lineage_id = sample.get("lineage_id")
        split = str(sample.get("split"))
        if image_path in seen_images and seen_images[image_path] != split:
            violations.append({"image_path": image_path, "reason": "same image appears in multiple splits", "first_split": seen_images[image_path], "second_split": split})
        seen_images[image_path] = split
        if lineage_id and lineage_id in seen_lineages and seen_lineages[lineage_id] != split:
            violations.append({"lineage_id": lineage_id, "reason": "same lineage appears in multiple splits", "first_split": seen_lineages[lineage_id], "second_split": split})
        if lineage_id:
            seen_lineages[lineage_id] = split
    return violations


def audit_action_replay(run_id: str) -> list[dict[str, Any]]:
    violations = []
    paths = [
        ROOT / "evidence" / "public-range" / "raw" / "local-gocaptcha-compatible-lab" / run_id / "gocaptcha-action-replay-metrics.json",
        ROOT / "evidence" / "public-range" / "raw" / "gocaptcha-local" / run_id / "gocaptcha-action-replay-metrics.json",
        ROOT / "evidence" / "public-range" / "raw" / "gocaptcha-official" / run_id / "gocaptcha-official-action-replay-metrics.json",
        ROOT / "evidence" / "public-range" / "raw" / "gocaptcha-official" / run_id / "gocaptcha-official-action-replay-records.jsonl",
        ROOT / "evidence" / "public-range" / "raw" / "opencaptchaworld" / run_id / "opencaptchaworld-action-replay-metrics.json",
        ROOT / "evidence" / "public-range" / "raw" / "opencaptchaworld" / run_id / "opencaptchaworld-action-replay-records.jsonl",
        ROOT / "evidence" / "public-range" / "raw" / "shumei-compatible-lab" / run_id / "shumei-compatible-lab-action-replay-records.jsonl",
        ROOT / "evidence" / "public-range" / "raw" / "aliyun-compatible-lab" / run_id / "aliyun-compatible-lab-action-replay-records.jsonl",
        ROOT / "evidence" / "public-range" / "raw" / "five-second-shield-lab" / run_id / "five-second-shield-action-records.jsonl",
        ROOT / "evidence" / "public-range" / "raw" / "captcha-vision-lab" / run_id / "action-replay-metrics.json",
    ]
    for path in paths:
        if not path.is_file():
            continue
        if path.suffix == ".jsonl":
            rows = []
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                if line.strip():
                    item = json.loads(line)
                    if isinstance(item, dict):
                        rows.append(item)
        else:
            payload = read_json(path)
            metrics = payload.get("metrics", {})
            rows = metrics.get("challenges") if isinstance(metrics.get("challenges"), list) else [metrics]
        for index, row in enumerate(rows):
            if row.get("label_read_for_prediction") not in {False, None}:
                violations.append({"source": str(path), "challenge_index": index, "reason": "action replay used label as prediction"})
            if row.get("dom_read_for_prediction") not in {False, None}:
                violations.append({"source": str(path), "challenge_index": index, "reason": "action replay used DOM answer"})
            if row.get("query_param_read_for_prediction") not in {False, None}:
                violations.append({"source": str(path), "challenge_index": index, "reason": "action replay used query expected"})
            if row.get("metadata_answer_read_for_prediction") not in {False, None}:
                violations.append({"source": str(path), "challenge_index": index, "reason": "action replay used metadata answer"})
            if row.get("server_expected_read_for_prediction") not in {False, None}:
                violations.append({"source": str(path), "challenge_index": index, "reason": "action replay used server expected"})
            if row.get("action_replay_expected_read_for_prediction") not in {False, None}:
                violations.append({"source": str(path), "challenge_index": index, "reason": "action replay used expected answer"})
            if row.get("challenge_config_answer_read_for_prediction") not in {False, None}:
                violations.append({"source": str(path), "challenge_index": index, "reason": "action replay used challenge answer config"})
            sources = set(row.get("solver_input_sources") or [])
            if sources and sources - ACTION_ALLOWED_SOURCES:
                violations.append({"source": str(path), "challenge_index": index, "reason": f"unexpected action replay solver sources {sorted(sources)}"})
    return violations


def update_public_evidence(run_id: str, status: str, report_path: Path) -> None:
    for path in (
        ROOT / "evidence" / "public-range" / "gocaptcha-local" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "gocaptcha-official" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "opencaptchaworld" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "local-gocaptcha-compatible-lab" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "captcha-vision-lab" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "shumei-compatible-lab" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "aliyun-compatible-lab" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "five-second-shield-lab" / f"{run_id}.json",
    ):
        if not path.is_file():
            continue
        payload = read_json(path)
        if not isinstance(payload, dict):
            continue
        payload["leakage_audit"] = {"status": status.lower(), "path": str(report_path)}
        if status != "PASS" and payload.get("capability_status") in {"positive_allowed", "positive_candidate", "positive_verified", "stable_positive"}:
            payload["capability_status"] = "negative_eval_only"
            if isinstance(payload.get("decision"), dict):
                payload["decision"]["skills_participation"] = "negative_eval_only"
                payload["decision"]["positive_allowed"] = False
                payload["decision"]["blocked_reason"] = "leakage audit failed; run invalid for positive capability"
        write_json(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit CAPTCHA leakage")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    run_id = args.run_id
    vision_dir = ROOT / "evidence" / "public-range" / "raw" / "captcha-vision-lab" / run_id
    manifest_path = vision_dir / "dataset-manifest.json"
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    action_paths = [
        ROOT / "evidence" / "public-range" / "raw" / "gocaptcha-official" / run_id / "gocaptcha-official-action-replay-records.jsonl",
        ROOT / "evidence" / "public-range" / "raw" / "opencaptchaworld" / run_id / "opencaptchaworld-action-replay-records.jsonl",
        ROOT / "evidence" / "public-range" / "raw" / "shumei-compatible-lab" / run_id / "shumei-compatible-lab-action-replay-records.jsonl",
        ROOT / "evidence" / "public-range" / "raw" / "aliyun-compatible-lab" / run_id / "aliyun-compatible-lab-action-replay-records.jsonl",
        ROOT / "evidence" / "public-range" / "raw" / "five-second-shield-lab" / run_id / "five-second-shield-action-records.jsonl",
    ]
    has_public_action_replay = any(path.is_file() for path in action_paths)
    if not manifest_path.is_file():
        manifest = {}
        if has_public_action_replay:
            warnings.append({"source": str(manifest_path), "reason": "dataset manifest not required for public-range-only action replay audit"})
        else:
            failures.append({"source": str(manifest_path), "reason": "missing dataset manifest"})
    else:
        manifest = read_json(manifest_path)
        failures.extend(split_contamination(manifest))
        leakage_policy = manifest.get("leakage_policy", {})
        if "label" not in leakage_policy.get("solver_must_not_read", []):
            warnings.append({"source": str(manifest_path), "reason": "manifest leakage policy does not explicitly ban label reads"})
    failures.extend(audit_predictions(vision_dir / "baseline-predictions.json", "baseline-predictions"))
    failures.extend(audit_predictions(vision_dir / "trained-predictions.json", "trained-predictions"))
    failures.extend(audit_action_replay(run_id))

    public_paths = [
        ROOT / "evidence" / "public-range" / "gocaptcha-local" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "gocaptcha-official" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "opencaptchaworld" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "captcha-vision-lab" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "shumei-compatible-lab" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "aliyun-compatible-lab" / f"{run_id}.json",
        ROOT / "evidence" / "public-range" / "five-second-shield-lab" / f"{run_id}.json",
    ]
    for path in public_paths:
        if path.is_file():
            payload = read_json(path)
            action = payload.get("action_replay", {}).get("metrics", {})
            if action.get("prediction_source") == "expected":
                failures.append({"source": str(path), "reason": "public range action replay used expected as prediction"})

    status = "PASS" if not failures else "INVALID"
    report = {
        "tool": "captcha_leakage_audit",
        "run_id": run_id,
        "status": status,
        "checked": {
            "label_path_reads": True,
            "metadata_answer_reads": True,
            "dom_answer_reads": True,
            "query_expected_reads": True,
            "action_expected_as_prediction": True,
            "train_test_contamination": True,
            "public_range_answer_leakage": True,
        },
        "failures": failures,
        "warnings": warnings,
        "decision": {
            "run_invalid": bool(failures),
            "positive_allowed": False if failures else None,
        },
    }
    out = ROOT / "evidence" / "public-range" / "raw" / "captcha-leakage-audit" / run_id / "leakage-audit.json"
    write_json(out, report)
    update_public_evidence(run_id, status, out)
    print(json.dumps({"status": status, "run_id": run_id, "report_path": str(out), "failure_count": len(failures)}, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
