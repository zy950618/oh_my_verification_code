from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from .authorization import AuthorizationRecord
from .common import ContractModel, EvidenceRef, FactClaim
from .enums import BusinessAcceptanceStatus, PromotionStatus


class AssertionResult(ContractModel):
    name: str
    passed: bool
    expected: str | None = None
    observed: str | None = None


class BusinessAcceptanceReceipt(ContractModel):
    schema_version: str = "captcha-business-acceptance-receipt/v1"
    receipt_id: str
    authorization_id: str
    attempt_id: str
    challenge_instance_id: str
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
        return self


class PromotionDecision(ContractModel):
    schema_version: str = "captcha-promotion-decision/v1"
    status: PromotionStatus
    business_acceptance_status: BusinessAcceptanceStatus
    authorization_id: str | None = None
    receipt_ids: list[str] = Field(default_factory=list)
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
    elif not authorization.production_allowed:
        blockers.append("authorization does not allow production execution")

    accepted = [receipt for receipt in receipts if receipt.accepted]
    if len(accepted) < repeat_required:
        blockers.append(f"requires {repeat_required} accepted first-party business receipts")
    rounds = {receipt.repeat_round for receipt in accepted}
    if accepted and len(rounds) < min(repeat_required, len(accepted)):
        blockers.append("repeat receipts must use distinct rounds")
    if authorization and any(receipt.authorization_id != authorization.authorization_id for receipt in accepted):
        blockers.append("receipt authorization does not match")
    if any(receipt.negative_control_ledger_delta != 0 for receipt in receipts):
        blockers.append("negative controls changed the business ledger")

    approved = not blockers
    return PromotionDecision(
        status=PromotionStatus.APPROVED if approved else PromotionStatus.INELIGIBLE,
        business_acceptance_status=(
            BusinessAcceptanceStatus.ACCEPTED if approved else BusinessAcceptanceStatus.NOT_ATTEMPTED
        ),
        authorization_id=authorization.authorization_id if authorization else None,
        receipt_ids=[receipt.receipt_id for receipt in accepted],
        blockers=blockers,
    )
