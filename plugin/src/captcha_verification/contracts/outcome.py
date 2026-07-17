from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from captcha_verification.canonical import artifact_hash

from .authorization import AuthorizationRecord
from .common import ContractModel, EvidenceRef, FactClaim
from .enums import BusinessAcceptanceStatus, PromotionStatus, ReceiptKind


class AssertionResult(ContractModel):
    name: str
    passed: bool
    expected: str | None = None
    observed: str | None = None


class BusinessAcceptanceReceipt(ContractModel):
    schema_version: str = "captcha-business-acceptance-receipt/v1"
    kind: Literal[ReceiptKind.BUSINESS] = ReceiptKind.BUSINESS
    audience: Literal["first_party_protected_data"] = "first_party_protected_data"
    receipt_id: str
    receipt_hash: str | None = None
    parent_provider_receipt_hash: str | None = None
    authorization_id: str
    attempt_id: str
    challenge_instance_id: str
    plan_hash: str | None = None
    provider_verification_receipt_id: str | None = None
    business_endpoint_id: str
    transport_status: int
    response_assertions: list[AssertionResult]
    ledger_assertions: list[AssertionResult]
    owner_id_hash: str
    session_id_hash: str
    worker_id: str
    object_id: str
    object_version: str
    ledger_index: int = Field(default=0, ge=0)
    negative_control_ledger_delta: int = 0
    repeat_round: int = Field(ge=1)
    accepted_at: datetime
    evidence: list[EvidenceRef] = Field(default_factory=list)
    facts: list[FactClaim] = Field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return (
            200 <= self.transport_status < 300
            and bool(self.response_assertions)
            and all(item.passed for item in self.response_assertions)
            and bool(self.ledger_assertions)
            and all(item.passed for item in self.ledger_assertions)
            and self.negative_control_ledger_delta == 0
        )

    @model_validator(mode="after")
    def require_assertions(self) -> "BusinessAcceptanceReceipt":
        if not self.response_assertions:
            raise ValueError("response_assertions must not be empty")
        if not self.ledger_assertions:
            raise ValueError("ledger_assertions must not be empty")
        expected = artifact_hash(self)
        if self.receipt_hash is None:
            self.receipt_hash = expected
        elif self.receipt_hash != expected:
            raise ValueError("business receipt hash does not match content")
        return self


class PromotionDecision(ContractModel):
    schema_version: str = "captcha-promotion-decision/v1"
    status: PromotionStatus
    business_acceptance_status: BusinessAcceptanceStatus
    scope: str = "first_party_local_reference_only"
    authorization_id: str | None = None
    receipt_ids: list[str] = Field(default_factory=list)
    challenge_instance_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    facts: list[FactClaim] = Field(default_factory=list)


def decide_promotion(
    *,
    authorization: AuthorizationRecord | None,
    receipts: list[BusinessAcceptanceReceipt],
    repeat_required: int = 2,
) -> PromotionDecision:
    blockers: list[str] = []
    if authorization is None:
        blockers.append("missing verified authorization record")
    elif authorization.status != "verified" or authorization.fact_level != "observed":
        blockers.append("authorization is not verified with observed evidence")

    accepted = [receipt for receipt in receipts if receipt.accepted]
    if len(accepted) < repeat_required:
        blockers.append(f"requires {repeat_required} accepted first-party business receipts")
    rounds = {receipt.repeat_round for receipt in accepted}
    challenges = {receipt.challenge_instance_id for receipt in accepted}
    if len(rounds) < min(repeat_required, len(accepted)):
        blockers.append("repeat receipts must use distinct rounds")
    if len(challenges) < min(repeat_required, len(accepted)):
        blockers.append("repeat receipts must use fresh challenge instances")
    if authorization and any(receipt.authorization_id != authorization.authorization_id for receipt in accepted):
        blockers.append("receipt authorization does not match")
    if any(receipt.negative_control_ledger_delta != 0 for receipt in receipts):
        blockers.append("negative controls changed the business ledger")
    if accepted and len({receipt.owner_id_hash for receipt in accepted}) != 1:
        blockers.append("business receipt ownership does not match across repeats")

    approved = not blockers
    return PromotionDecision(
        status=PromotionStatus.APPROVED if approved else PromotionStatus.INELIGIBLE,
        business_acceptance_status=(
            BusinessAcceptanceStatus.ACCEPTED if approved else BusinessAcceptanceStatus.NOT_ATTEMPTED
        ),
        authorization_id=authorization.authorization_id if authorization else None,
        receipt_ids=[receipt.receipt_id for receipt in accepted],
        challenge_instance_ids=[receipt.challenge_instance_id for receipt in accepted],
        blockers=blockers,
    )
