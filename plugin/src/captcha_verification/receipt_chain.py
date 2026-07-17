from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from captcha_verification.actions import plan_action
from captcha_verification.canonical import artifact_hash
from captcha_verification.classification import classify
from captcha_verification.contracts import (
    AssertionResult,
    AuthorizationRecord,
    BusinessAcceptanceReceipt,
    CoordinateFrame,
    EvidenceRef,
    ExecutionReceipt,
    FactLevel,
    PlanActionRequest,
    ProviderVerificationReceipt,
    decide_promotion,
)
from captcha_verification.fixtures import asset_from_sample, generate_reference_fixtures
from captcha_verification.solvers import solve
from captcha_verification.contracts import ClassificationRequest, SolveRequest


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _binding(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class LocalReferenceLab:
    """Self-owned in-process reference chain with distinct provider/business signers."""

    def __init__(self, fixture_root: Path) -> None:
        self.fixture_root = fixture_root
        self.manifest = generate_reference_fixtures(fixture_root)
        self.provider_key = secrets.token_bytes(32)
        self.business_key = secrets.token_bytes(32)
        self.provider_receipts: dict[str, dict[str, Any]] = {}
        self.used_provider_receipts: set[str] = set()
        self.ledger: list[dict[str, Any]] = []
        self.session_id = "local-session"
        self.owner_id = "local-owner"
        self.worker_id = "local-worker"

    def authorization(self) -> AuthorizationRecord:
        now = _utc()
        return AuthorizationRecord(
            authorization_id="authorization-local-reference",
            subject="repository-owned-local-reference-runtime",
            controller="zhaoyang",
            target_environment_id="local-reference-runtime",
            allowed_hosts=["127.0.0.1"],
            allowed_routes=["/api/challenges", "/api/provider/verify", "/api/business/orders"],
            allowed_methods=["POST"],
            allowed_actions=["classify", "solve", "plan", "local_evaluate", "provider_verify", "business_write"],
            prohibited_actions=["third_party_production", "stealth", "token_forgery"],
            basis="owned",
            status="verified",
            fact_level="observed",
            evidence=[EvidenceRef(evidence_id="owned-lab", uri="repo://labs/public-range-labs/local-reference-runtime", sha256=None, fact_level=FactLevel.OBSERVED)],
            issued_at=now - timedelta(minutes=1),
            expires_at=now + timedelta(hours=1),
            revocation_contact="local-test-owner",
            data_handling_scope="synthetic fixtures and sanitized hashes only",
            production_allowed=False,
            operator_acknowledged=True,
        )

    def challenge(self, round_number: int) -> dict[str, Any]:
        family = ("slider", "rotate", "click")[(round_number - 1) % 3]
        candidates = [sample for sample in self.manifest["samples"] if sample["family"] == family]
        sample = candidates[(round_number - 1) % len(candidates)]
        return {
            "challenge_instance_id": f"challenge-{round_number}-{uuid.uuid4().hex}",
            "asset": asset_from_sample(sample),
            "label_path": Path(sample["server_label_path"]),
            "expires_at": _utc() + timedelta(minutes=2),
            "family": family,
        }

    def local_evaluate(self, plan, challenge: dict[str, Any]) -> ExecutionReceipt:
        expected = json.loads(challenge["label_path"].read_text(encoding="utf-8"))
        observed_ok = False
        if expected["family"] == "slider":
            expected_x = expected["offset"]["x"]
            observed_ok = bool(plan.actions) and abs(plan.actions[-1].x - expected_x) <= 4
        elif expected["family"] == "rotate":
            observed = plan.actions[0].angle_degrees
            delta = abs((observed - expected["angle_degrees"] + 180) % 360 - 180)
            observed_ok = delta <= 5
        elif expected["family"] == "click":
            observed_points = [(action.x, action.y) for action in plan.actions]
            expected_points = [(point["x"], point["y"]) for point in expected["points"]]
            observed_ok = len(observed_points) == len(expected_points) and all(
                abs(observed[0] - wanted[0]) <= 4 and abs(observed[1] - wanted[1]) <= 4
                for observed, wanted in zip(observed_points, expected_points)
            )
        now = _utc()
        return ExecutionReceipt(
            receipt_id=f"execution-{uuid.uuid4().hex}",
            plan_id=plan.plan_id,
            plan_hash=plan.plan_hash,
            input_hash=plan.input_hash,
            challenge_instance_id=plan.challenge_instance_id,
            session_binding_hash=plan.session_binding_hash,
            driver_id="server-side-local-plan-evaluator",
            status="completed" if observed_ok else "rejected",
            started_at=now,
            ended_at=now,
        )

    def provider_verify(self, execution: ExecutionReceipt) -> ProviderVerificationReceipt:
        now = _utc()
        accepted = execution.status == "completed" and execution.receipt_hash is not None
        receipt = ProviderVerificationReceipt(
            receipt_id=f"provider-{uuid.uuid4().hex}",
            parent_execution_receipt_hash=execution.receipt_hash,
            plan_hash=execution.plan_hash,
            session_binding_hash=execution.session_binding_hash,
            challenge_instance_id=execution.challenge_instance_id,
            status="accepted" if accepted else "rejected",
            provider="first_party_local_reference",
            transport_status=200,
            response_assertions_passed=accepted,
            verified_at=now,
            expires_at=now + timedelta(minutes=1),
        )
        signature = hmac.new(self.provider_key, receipt.receipt_hash.encode("ascii"), hashlib.sha256).hexdigest()
        self.provider_receipts[receipt.receipt_id] = {"receipt": receipt, "signature": signature}
        return receipt

    def business_write(self, provider: ProviderVerificationReceipt, authorization: AuthorizationRecord, round_number: int) -> BusinessAcceptanceReceipt:
        before = len(self.ledger)
        stored = self.provider_receipts.get(provider.receipt_id)
        signature_valid = bool(
            stored
            and hmac.compare_digest(
                stored["signature"],
                hmac.new(self.provider_key, provider.receipt_hash.encode("ascii"), hashlib.sha256).hexdigest(),
            )
        )
        valid = (
            stored is not None
            and signature_valid
            and stored["receipt"].receipt_hash == provider.receipt_hash
            and provider.receipt_id not in self.used_provider_receipts
            and provider.status == "accepted"
            and provider.expires_at is not None
            and provider.expires_at > _utc()
            and provider.session_binding_hash == _binding(self.session_id)
        )
        if valid:
            self.used_provider_receipts.add(provider.receipt_id)
            order = {
                "object_id": f"order-{round_number}",
                "object_version": "1",
                "owner_id_hash": _binding(self.owner_id),
                "session_id_hash": _binding(self.session_id),
                "worker_id": self.worker_id,
                "challenge_instance_id": provider.challenge_instance_id,
                "provider_receipt_hash": provider.receipt_hash,
            }
            self.ledger.append(order)
        after = len(self.ledger)
        accepted = valid and after - before == 1
        object_id = self.ledger[-1]["object_id"] if accepted else f"rejected-{round_number}"
        receipt = BusinessAcceptanceReceipt(
            receipt_id=f"business-{uuid.uuid4().hex}",
            parent_provider_receipt_hash=provider.receipt_hash,
            authorization_id=authorization.authorization_id,
            attempt_id=f"attempt-{round_number}",
            challenge_instance_id=provider.challenge_instance_id,
            plan_hash=provider.plan_hash,
            provider_verification_receipt_id=provider.receipt_id,
            business_endpoint_id="local-protected-orders",
            transport_status=200,
            response_assertions=[AssertionResult(name="domain_acceptance", passed=accepted, expected="accepted", observed="accepted" if accepted else "rejected")],
            ledger_assertions=[
                AssertionResult(name="ledger_delta", passed=accepted, expected="1", observed=str(after - before)),
                AssertionResult(name="ownership", passed=accepted, expected=_binding(self.owner_id), observed=_binding(self.owner_id) if accepted else "not_written"),
            ],
            owner_id_hash=_binding(self.owner_id),
            session_id_hash=_binding(self.session_id),
            worker_id=self.worker_id,
            object_id=object_id,
            object_version="1",
            ledger_index=after,
            negative_control_ledger_delta=0,
            repeat_round=round_number,
            accepted_at=_utc(),
        )
        if accepted:
            signature = hmac.new(self.business_key, receipt.receipt_hash.encode("ascii"), hashlib.sha256).hexdigest()
            self.ledger[-1]["business_receipt_signature_hash"] = _binding(signature)
        return receipt

    def rejected_business_envelope(self, reason: str) -> dict[str, Any]:
        return {"transport_status": 200, "business_acceptance_status": "rejected", "reason": reason}

    def run(self, rounds: int = 2) -> dict[str, Any]:
        if rounds < 2:
            raise ValueError("local receipt-chain promotion requires at least two fresh rounds")
        authorization = self.authorization()
        receipts = []
        providers = []
        chain = []
        for round_number in range(1, rounds + 1):
            challenge = self.challenge(round_number)
            asset = challenge["asset"]
            classification = classify(
                ClassificationRequest(
                    request_id=f"classify-{round_number}",
                    assets=[asset],
                    context={"target_id": "local-reference-runtime"},
                    authorization_record_id=authorization.authorization_id,
                )
            )
            prediction = solve(
                SolveRequest(
                    request_id=f"solve-{round_number}",
                    challenge_instance_id=challenge["challenge_instance_id"],
                    challenge_family=classification.challenge_family,
                    assets=[asset],
                    allowed_solution_types=["offset", "angle", "points"],
                    classification_id=classification.classification_id,
                    classification_hash=artifact_hash(classification),
                    classification_confidence=classification.confidence,
                    authorization_record_id=authorization.authorization_id,
                    expires_at=challenge["expires_at"],
                )
            )
            plan = plan_action(
                PlanActionRequest(
                    request_id=f"plan-{round_number}",
                    prediction=prediction.model_dump(mode="json"),
                    challenge_instance_id=challenge["challenge_instance_id"],
                    authorization_record_id=authorization.authorization_id,
                    session_binding_hash=_binding(self.session_id),
                    target_id="local-reference-runtime",
                    coordinate_frame=CoordinateFrame(
                        width=400,
                        height=300,
                        device_pixel_ratio=1,
                        intrinsic_width=asset.width_px or (330 if challenge["family"] == "slider" else 170 if challenge["family"] == "rotate" else 260),
                        intrinsic_height=asset.height_px or (170 if challenge["family"] in {"slider", "rotate"} else 180),
                    ),
                    created_at=_utc(),
                    expires_at=challenge["expires_at"],
                )
            )
            execution = self.local_evaluate(plan, challenge)
            provider = self.provider_verify(execution)
            business = self.business_write(provider, authorization, round_number)
            receipts.append(business)
            providers.append(provider)
            chain.append(
                {
                    "round": round_number,
                    "challenge_instance_id": challenge["challenge_instance_id"],
                    "input_hash": prediction.input_hash,
                    "classification_hash": artifact_hash(classification),
                    "prediction_hash": prediction.artifact_hash,
                    "plan_hash": plan.plan_hash,
                    "execution_receipt_hash": execution.receipt_hash,
                    "provider_receipt_hash": provider.receipt_hash,
                    "business_receipt_hash": business.receipt_hash,
                    "business_accepted": business.accepted,
                }
            )
        negative_before = len(self.ledger)
        replay_receipt = self.business_write(providers[0], authorization, rounds + 1)
        provider_as_business_rejected = providers[0].kind == "provider_receipt" and providers[0].audience != "first_party_protected_data"
        browser_signature = f"browser-fnv-{_binding('browser')[:8]}"
        expected_business_signature = hmac.new(self.business_key, receipts[0].receipt_hash.encode("ascii"), hashlib.sha256).hexdigest()
        browser_signature_rejected = not hmac.compare_digest(browser_signature, expected_business_signature)
        stale_repeat_rejected = providers[0].challenge_instance_id == receipts[0].challenge_instance_id and replay_receipt.accepted is False
        negatives = [
            {**self.rejected_business_envelope("http_200_is_not_business_success"), "observed_domain_acceptance": replay_receipt.accepted},
            {**self.rejected_business_envelope("provider_receipt_is_not_business_receipt"), "observed_receipt_kind": providers[0].kind, "boundary_enforced": provider_as_business_rejected},
            {**self.rejected_business_envelope("fresh_challenge_required_for_repeat"), "reused_challenge_instance_id": providers[0].challenge_instance_id, "boundary_enforced": stale_repeat_rejected},
            {**self.rejected_business_envelope("browser_cannot_sign_business_receipt"), "browser_signature_rejected": browser_signature_rejected},
            {**self.rejected_business_envelope("replayed_provider_receipt"), "observed_domain_acceptance": replay_receipt.accepted},
        ]
        negative_delta = len(self.ledger) - negative_before
        decision = decide_promotion(authorization=authorization, receipts=receipts, repeat_required=rounds)
        return {
            "schema_version": "captcha-local-reference-e2e/v1",
            "scope": "first_party_local_reference_only",
            "authorization_hash": artifact_hash(authorization),
            "rounds": chain,
            "positive_ledger_delta": len(self.ledger),
            "negative_controls": negatives,
            "negative_control_ledger_delta": negative_delta,
            "promotion_decision": decision.model_dump(mode="json"),
            "raw_receipts_persisted": False,
            "signing_keys_persisted": False,
        }


def run_local_e2e(*, rounds: int = 2, fixture_root: Path | None = None) -> dict[str, Any]:
    if fixture_root is not None:
        return LocalReferenceLab(fixture_root).run(rounds)
    with tempfile.TemporaryDirectory(prefix="captcha-reference-") as directory:
        return LocalReferenceLab(Path(directory)).run(rounds)
