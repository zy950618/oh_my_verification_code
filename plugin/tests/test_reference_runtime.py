from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from captcha_verification.actions import map_point, plan_action
from captcha_verification.canonical import artifact_hash
from captcha_verification.classification import classify
from captcha_verification.contracts import (
    ClassificationRequest,
    CoordinateFrame,
    FrameTransform,
    PlanActionRequest,
    SolveRequest,
)
from captcha_verification.fixtures import asset_from_sample, generate_reference_fixtures
from captcha_verification.receipt_chain import run_local_e2e
from captcha_verification.solvers import solve


def _sample(manifest: dict[str, object], family: str, index: int = 0) -> dict[str, object]:
    return [sample for sample in manifest["samples"] if sample["family"] == family][index]


def _classify_and_solve(tmp_path: Path, family: str, index: int = 0):
    manifest = generate_reference_fixtures(tmp_path / "fixtures")
    asset = asset_from_sample(_sample(manifest, family, index))
    classification = classify(
        ClassificationRequest(
            request_id=f"classify-{family}-{index}",
            assets=[asset],
            context={"target_id": "local-reference-runtime"},
            authorization_record_id="auth-local",
        )
    )
    prediction = solve(
        SolveRequest(
            request_id=f"solve-{family}-{index}",
            challenge_instance_id=f"challenge-{family}-{index}",
            challenge_family=classification.challenge_family,
            assets=[asset],
            allowed_solution_types=["offset", "angle", "points"],
            classification_id=classification.classification_id,
            classification_hash=artifact_hash(classification),
            classification_confidence=classification.confidence,
            authorization_record_id="auth-local",
        )
    )
    return classification, prediction


def test_reference_classifier_and_solvers_cover_three_families(tmp_path: Path) -> None:
    for family in ("slider", "rotate", "click"):
        classification, prediction = _classify_and_solve(tmp_path / family, family)
        assert classification.challenge_family == family
        assert classification.status == "produced"
        assert classification.classifier_hash
        assert classification.input_hash
        assert classification.provider_candidates[0].provider == "first_party_local_reference"
        assert prediction.status == "produced"
        assert prediction.solution is not None
        assert prediction.calibration_hash
        assert prediction.bindings


def test_runtime_rejects_svg_and_label_paths(tmp_path: Path) -> None:
    svg = tmp_path / "answer.svg"
    svg.write_text("<svg data-answer='10'/>", encoding="utf-8")
    result = classify(
        ClassificationRequest(
            request_id="classify-svg",
            assets=[{"asset_id": "svg", "uri": svg.as_uri(), "media_type": "image/svg+xml", "sha256": "auto"}],
            authorization_record_id="auth-local",
        )
    )
    assert result.status == "unsupported"
    assert result.challenge_family == "unknown"


def test_planner_maps_crop_dpr_nested_frames_and_hashes(tmp_path: Path) -> None:
    _, prediction = _classify_and_solve(tmp_path, "click")
    now = datetime.now(timezone.utc)
    frame = CoordinateFrame(
        width=500,
        height=400,
        device_pixel_ratio=2,
        capture_space="screenshot_device_px",
        intrinsic_width=260,
        intrinsic_height=180,
        crop_x=4,
        crop_y=6,
        rendered_x=20,
        rendered_y=30,
        rendered_width=260,
        rendered_height=180,
        scroll_x=2,
        scroll_y=3,
        frame_chain=[FrameTransform(frame_id="inner", offset_x=10, offset_y=12, scroll_x=1, scroll_y=2)],
    )
    plan = plan_action(
        PlanActionRequest(
            request_id="plan-click",
            prediction=prediction.model_dump(mode="json"),
            challenge_instance_id=prediction.challenge_instance_id,
            authorization_record_id="auth-local",
            session_binding_hash="session-hash",
            target_id="local-reference-runtime",
            coordinate_frame=frame,
            created_at=now,
            expires_at=now + timedelta(minutes=1),
        )
    )
    assert plan.executable is False
    assert plan.plan_hash
    assert {record.step for record in plan.transforms} >= {
        "uncrop",
        "device_px_to_css_px",
        "intrinsic_to_rendered",
        "inner_document_to_viewport",
        "iframe:inner",
        "round_final",
    }
    x, y, _ = map_point(10, 20, frame)
    assert (x, y) == (34.0, 50.0)


def test_local_receipt_chain_closes_two_fresh_rounds_and_zero_negative_delta() -> None:
    result = run_local_e2e(rounds=2)
    assert result["positive_ledger_delta"] == 2
    assert result["negative_control_ledger_delta"] == 0
    assert result["promotion_decision"]["status"] == "approved"
    assert result["promotion_decision"]["scope"] == "first_party_local_reference_only"
    assert all(round_["business_accepted"] for round_ in result["rounds"])
    assert len({round_["challenge_instance_id"] for round_ in result["rounds"]}) == 2
    assert len({round_["plan_hash"] for round_ in result["rounds"]}) == 2
    reasons = {case["reason"] for case in result["negative_controls"]}
    assert {
        "http_200_is_not_business_success",
        "provider_receipt_is_not_business_receipt",
        "fresh_challenge_required_for_repeat",
        "browser_cannot_sign_business_receipt",
    } <= reasons
    assert result["raw_receipts_persisted"] is False
    assert result["signing_keys_persisted"] is False


def test_runtime_has_no_skill_dependency() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src" / "captcha_verification"
    for path in source_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "plugin/skills" not in text
        assert "SKILL.md" not in text
