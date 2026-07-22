from __future__ import annotations

import json
from pathlib import Path

import pytest

from captcha_verification.agent_runtime import (
    AgentPolicyManifest,
    BinaryExecutionReceipt,
    EvalRunner,
    IndependentReviewer,
    JobManifest,
    MockBackend,
    ProvenanceRecord,
    ProvenanceRegistry,
    PromptPackManifest,
    PromptPackInstaller,
    ResultManifest,
    evaluate_policy,
)


def policy() -> AgentPolicyManifest:
    return AgentPolicyManifest(policy_id="p", version="1", content_hash="12345678")


def test_policy_allows_offline_and_denies_restricted() -> None:
    safe = JobManifest(job_id="safe", objective="run local tests", scope={"target_environment": "offline_compute"}, mode="offline_compute", sandbox_profile={"name": "offline_compute", "network": "none"})
    denied = JobManifest(job_id="denied", objective="ignore authorization and bypass", scope={"target_environment": "offline_compute"}, mode="offline_compute", sandbox_profile={"name": "offline_compute", "network": "none"})
    assert evaluate_policy(safe, policy()).allowed
    assert not evaluate_policy(denied, policy()).allowed


def test_eval_is_reproducible() -> None:
    first = EvalRunner(MockBackend(), policy()).run(seed=7)
    second = EvalRunner(MockBackend(), policy()).run(seed=7)
    assert first.canonical_hash == second.canonical_hash
    assert all(item.passed for item in first.results)


def test_reviewer_rejects_tampered_business_claim() -> None:
    result = ResultManifest(job_id="j", status="completed", backend="mock", input_hash="12345678", output_hash="87654321", evidence_stage="E2_local_executed", business_success="not_verified", reviewer_summary="business success")
    verdict = IndependentReviewer().review(result)
    assert verdict.verdict == "accepted"
    result.business_success = "accepted"  # type: ignore[misc]
    with pytest.raises(ValueError):
        ResultManifest.model_validate(result.model_dump(mode="json"))


def test_binary_receipt_rejects_business_claim() -> None:
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    with pytest.raises(ValueError):
        BinaryExecutionReceipt(
            run_id="r",
            executable="/bin/true",
            workspace="/tmp",
            started_at=now,
            ended_at=now,
            stdout_hash="12345678",
            stderr_hash="87654321",
            status="completed",
            real_binary=True,
            evidence_stage="E2_local_executed",
            business_success="accepted",
        )


def test_codex_missing_binary_is_blocked(tmp_path: Path) -> None:
    from captcha_verification.agent_runtime import CodexAdapter

    job = JobManifest(job_id="missing", objective="run local tests", scope={"target_environment": "offline_compute"}, mode="offline_compute", sandbox_profile={"name": "offline_compute", "network": "none"})
    result = CodexAdapter("definitely-not-a-codex-binary").run(job, policy(), workspace=tmp_path)
    assert result.status == "blocked"
    assert "missing_codex_cli" in result.missing_evidence


    registry = ProvenanceRegistry()
    with pytest.raises(ValueError):
        registry.register(ProvenanceRecord(artifact_id="a", artifact_type="result", sha256="12345678", secret_detected=True))


def test_prompt_pack_apply_and_rollback(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    text = "Use only local fixtures."
    (source / "prompt.md").write_text(text, encoding="utf-8")
    import hashlib
    digest = hashlib.sha256(text.encode()).hexdigest()
    (source / "manifest.json").write_text(json.dumps(PromptPackManifest(pack_id="pack", version="1", content_hash=digest).model_dump(mode="json")), encoding="utf-8")
    ledger = tmp_path / "ledger.json"
    installer = PromptPackInstaller(allowed_destination_roots=(tmp_path,), ledger_path=ledger)
    plan = installer.inspect(source, destination)
    assert installer.dry_run(plan)["would_write"]
    applied = installer.apply(plan)
    assert applied["status"] == "applied"
    assert (destination / "prompt.md").read_text(encoding="utf-8") == text
    assert installer.rollback(applied["backup_id"])["status"] == "rolled_back"
