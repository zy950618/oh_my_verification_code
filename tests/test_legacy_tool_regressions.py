from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

flywheel = importlib.import_module("captcha_flywheel_common")
collector = importlib.import_module("captcha_failure_collector")
splitter = importlib.import_module("captcha_dataset_splitter")
leakage = importlib.import_module("captcha_leakage_audit")
trainer = importlib.import_module("captcha_model_trainer")


@pytest.fixture
def replay_module(monkeypatch):
    solver = types.ModuleType("captcha_vision_baseline_solver")
    solver.solve_click = lambda path: ([], 0.0)
    solver.solve_rotate = lambda path: (0, 0.0)
    solver.solve_slider = lambda path: ({"x": 0}, 0.0)
    monkeypatch.setitem(sys.modules, "captcha_vision_baseline_solver", solver)
    sys.modules.pop("captcha_action_replay_lab", None)
    return importlib.import_module("captcha_action_replay_lab")


def test_sample_base_groups_ten_samples_by_lineage() -> None:
    records = [
        flywheel.sample_base("run-1", "dataset-1", index, "local-target", "slider", "hard")
        for index in range(11)
    ]
    assert len({record["lineage_id"] for record in records[:10]}) == 1
    assert len({record["split"] for record in records[:10]}) == 1
    assert records[10]["lineage_id"] != records[0]["lineage_id"]
    assert records[0] == flywheel.sample_base(
        "run-1", "dataset-1", 0, "local-target", "slider", "hard"
    )
    assert records[0]["label_source"] == "deterministic_generator"
    assert records[0]["acquisition_mode"] == "synthetic"
    assert len(records[0]["lineage_id"]) == 16


@pytest.mark.parametrize("expected", ["train", "val", "test"])
def test_deterministic_split_reaches_each_bucket(expected: str) -> None:
    group_id = next(
        f"group-{index}"
        for index in range(10_000)
        if flywheel.deterministic_split(f"group-{index}") == expected
    )
    assert flywheel.deterministic_split(group_id) == expected


def test_dataset_splitter_preserves_lineage_groups(tmp_path: Path, monkeypatch) -> None:
    dataset_root = tmp_path / "dataset"
    run_id = "run-1"
    manifest_path = dataset_root / "manifests" / run_id / "dataset_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_id": "dataset-1",
                "samples": [
                    {"sample_id": "sample-a", "lineage_id": "shared-lineage"},
                    {"sample_id": "sample-b", "lineage_id": "shared-lineage"},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(splitter, "DATASET_ROOT", dataset_root)
    monkeypatch.setattr(sys, "argv", ["captcha_dataset_splitter.py", "--run-id", run_id])

    assert splitter.main() == 0
    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len({sample["split"] for sample in updated["samples"]}) == 1
    split_manifest = json.loads(
        (dataset_root / "splits" / run_id / "split_manifest.json").read_text(encoding="utf-8")
    )
    assert split_manifest["strategy"] == "sha256(lineage_id_or_sample_id)_70_15_15"
    assert split_manifest["leakage_check"]["split_uses_lineage_or_sample_hash"] is True


def test_leakage_audit_detects_lineage_cross_split() -> None:
    violations = leakage.split_contamination(
        {
            "samples": [
                {"image_path": "a.png", "lineage_id": "shared", "split": "train"},
                {"image_path": "b.png", "lineage_id": "shared", "split": "test"},
            ]
        }
    )
    assert violations == [
        {
            "lineage_id": "shared",
            "reason": "same lineage appears in multiple splits",
            "first_split": "train",
            "second_split": "test",
        }
    ]


def test_legacy_trainer_predictions_are_leakage_tainted(tmp_path: Path) -> None:
    image = tmp_path / "sample.svg"
    image.write_text(
        "<svg><rect data-name='red' x='10' y='20' width='40' height='40' fill='#f00'/></svg>",
        encoding="utf-8",
    )
    sample = {
        "sample_id": "sample-1",
        "family": "select",
        "difficulty": "easy",
        "split": "test",
        "image_path": str(image),
        "instruction": "select red",
        "label": {"type": "select_option_index", "target_index": 0},
    }

    prediction = trainer.metrics([sample], {"fallback_color": "blue"})["predictions"][0]
    assert prediction["solver_input_sources"] == [
        "raw_svg",
        "instruction_text",
        "svg_data_name",
        "svg_geometry",
    ]
    assert prediction["dom_read_for_prediction"] is True
    assert prediction["metadata_answer_read_for_prediction"] is True
    assert prediction["label_read_for_prediction"] is False


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def test_failure_collection_is_scoped_to_source_run(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "raw"
    filename = "shumei-compatible-lab-action-replay-records.jsonl"
    _write_jsonl(
        root / "shumei-compatible-lab" / "requested-run" / filename,
        [{"sample_id": "wanted", "success": False}, {"sample_id": "success", "success": True}],
    )
    _write_jsonl(
        root / "shumei-compatible-lab" / "decoy-run" / filename,
        [{"sample_id": "decoy", "success": False}],
    )
    monkeypatch.setattr(collector, "RAW_EVIDENCE_ROOT", root)

    failures = collector.parse_existing_failures("requested-run")
    assert [failure["sample_id"] for failure in failures] == ["wanted"]
    assert failures[0]["source_run_id"] == "requested-run"
    assert failures[0]["target_id"] == "shumei-compatible-lab"


def test_failure_manifest_reports_synthetic_provenance(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(collector, "DATASET_ROOT", tmp_path / "dataset")
    samples = [
        {
            "family": "slider",
            "split": "train",
            "target_id": "local-compatible-lab",
            "acquisition_mode": "synthetic",
        },
        {
            "family": "click",
            "split": "test",
            "target_id": "gocaptcha-official",
            "acquisition_mode": "observed",
        },
    ]

    path = collector.write_manifests("run-1", samples, [])
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["synthetic_count"] == 1
    assert manifest["label_source"] == "deterministic_generator"
    assert manifest["provenance_status"] == "synthetic_programmatic_labels"
    assert manifest["train_count"] == 1
    assert manifest["test_count"] == 1
    assert manifest["public_range_count"] == 1
    assert manifest["compatible_lab_count"] == 1


def test_action_record_uses_local_metric_feedback(monkeypatch, replay_module) -> None:
    monkeypatch.setattr(replay_module, "solve_slider", lambda path: ({"x": 12}, 0.9))
    passing = replay_module.action_record(
        "slide",
        {"image_path": "fixture.png", "offset": {"x": 12}},
        "challenge-pass",
    )
    failing = replay_module.action_record(
        "slide",
        {"image_path": "fixture.png", "offset": {"x": 30}},
        "challenge-fail",
    )
    assert passing["feedback_state"] == "local_metric_pass"
    assert passing["success"] is True
    assert failing["feedback_state"] == "local_metric_fail"
    assert failing["success"] is False
    assert "backend_accepted" not in json.dumps([passing, failing])


def test_failed_batch_evidence_is_consistent(tmp_path: Path, monkeypatch, replay_module) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(replay_module, "select_samples", lambda *args: [{"sample_id": "sample"}])
    monkeypatch.setattr(
        replay_module,
        "action_record",
        lambda kind, sample, challenge_id: {"kind": kind, "success": False, "error": 99.0},
    )
    monkeypatch.setattr(
        replay_module,
        "summarize_records",
        lambda records: {
            kind: {"threshold_pass": False}
            for kind in ("slide", "click", "rotate", "drag_drop")
        },
    )

    async def smoke(*args):
        return {"url": "http://127.0.0.1/", "screenshots": [], "trace_path": "", "network": {}}

    monkeypatch.setattr(replay_module, "run_gocaptcha_smoke_browser", smoke)
    args = types.SimpleNamespace(
        run_id="failed-run",
        difficulty="hard",
        samples_per_type=1,
        evidence_root=tmp_path / "evidence",
    )

    evidence = replay_module.asyncio.run(replay_module.run_gocaptcha_batch_target(args, {"samples": []}))
    assert evidence["execution_status"] == "REAL_EXECUTION_FAIL"
    assert evidence["control_flow_status"] == "CONTROL_FLOW_FAIL"
    assert evidence["capability_status"] == "negative_eval_only"
    assert evidence["execution_proof"]["exit_code"] == 1
    assert evidence["action_replay"]["status"] == "fail"
    assert evidence["action_replay"]["metrics"]["action_success"] is False
    assert evidence["ui_api_parity"]["status"] == "fail"
    assert "did not meet every required metric threshold" in evidence["decision"]["blocked_reason"]

    card = tmp_path / "experience/skills-experience/public-range-action-replay/failed-run/local-gocaptcha-compatible-lab-action-replay.yaml"
    assert "capability_status: negative_eval_only" in card.read_text(encoding="utf-8")


def test_main_returns_failure_for_failed_replay(monkeypatch, replay_module) -> None:
    async def failed_replay(args):
        return {"action_replay": {"status": "fail"}}

    monkeypatch.setattr(replay_module, "replay", failed_replay)
    monkeypatch.setattr(
        sys,
        "argv",
        ["captcha_action_replay_lab.py", "--predictions", "predictions.json", "--metrics", "metrics.json"],
    )
    assert replay_module.main() == 1
