from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from captcha_verification.contracts import (
    AssertionResult,
    AuthorizationRecord,
    BusinessAcceptanceReceipt,
    EvidenceRef,
    FactLevel,
    PromotionStatus,
    decide_promotion,
)


def verified_authorization() -> AuthorizationRecord:
    now = datetime.now(timezone.utc)
    return AuthorizationRecord(
        authorization_id="auth-1",
        subject="partner",
        controller="integration-owner",
        target_environment_id="owned-integration",
        allowed_hosts=["integration.example.test"],
        allowed_routes=["/search"],
        allowed_methods=["POST"],
        allowed_actions=["submit"],
        prohibited_actions=["stealth"],
        basis="written_contract",
        status="verified",
        fact_level="observed",
        evidence=[EvidenceRef(evidence_id="e-1", uri="private://authorization/auth-1", fact_level="observed")],
        issued_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
        revocation_contact="owner@example.test",
        data_handling_scope="redacted integration evidence",
        production_allowed=True,
        operator_acknowledged=True,
    )


def receipt(round_number: int, *, ledger_delta: int = 0) -> BusinessAcceptanceReceipt:
    return BusinessAcceptanceReceipt(
        receipt_id=f"receipt-{round_number}",
        authorization_id="auth-1",
        attempt_id=f"attempt-{round_number}",
        challenge_instance_id=f"challenge-{round_number}",
        business_endpoint_id="search",
        transport_status=200,
        response_assertions=[AssertionResult(name="result", passed=True)],
        ledger_assertions=[AssertionResult(name="owner", passed=True)],
        owner_id_hash="owner-hash",
        session_id_hash=f"session-{round_number}",
        worker_id=f"worker-{round_number}",
        object_id=f"object-{round_number}",
        object_version="1",
        negative_control_ledger_delta=ledger_delta,
        repeat_round=round_number,
        accepted_at=datetime.now(timezone.utc),
    )


def test_oral_claim_cannot_enable_production() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="oral claims cannot enable production"):
        AuthorizationRecord(
            authorization_id="auth-oral",
            subject="claimant",
            controller="claimant",
            target_environment_id="external",
            basis="oral_claim",
            status="claimed_unverified",
            fact_level="unverified",
            issued_at=now,
            expires_at=now + timedelta(days=1),
            revocation_contact="unknown",
            data_handling_scope="unknown",
            production_allowed=True,
        )


def test_http_200_without_assertions_is_not_a_receipt() -> None:
    with pytest.raises(ValueError, match="response_assertions"):
        BusinessAcceptanceReceipt(
            receipt_id="bad",
            authorization_id="auth-1",
            attempt_id="attempt",
            challenge_instance_id="challenge",
            business_endpoint_id="search",
            transport_status=200,
            response_assertions=[],
            ledger_assertions=[AssertionResult(name="ledger", passed=True)],
            owner_id_hash="owner",
            session_id_hash="session",
            worker_id="worker",
            object_id="object",
            object_version="1",
            repeat_round=1,
            accepted_at=datetime.now(timezone.utc),
        )


def test_promotion_requires_fresh_repeat_receipts() -> None:
    authorization = verified_authorization()
    incomplete = decide_promotion(authorization=authorization, receipts=[receipt(1)])
    assert incomplete.status == PromotionStatus.INELIGIBLE
    assert incomplete.business_acceptance_status == "not_attempted"

    approved = decide_promotion(authorization=authorization, receipts=[receipt(1), receipt(2)])
    assert approved.status == PromotionStatus.APPROVED
    assert approved.business_acceptance_status == "accepted"


def test_negative_control_ledger_delta_blocks_promotion() -> None:
    decision = decide_promotion(
        authorization=verified_authorization(),
        receipts=[receipt(1), receipt(2, ledger_delta=1)],
    )
    assert decision.status == PromotionStatus.INELIGIBLE
    assert "negative controls changed the business ledger" in decision.blockers
