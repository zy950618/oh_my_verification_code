from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import FactLevel, OperationStatus


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class FactClaim(ContractModel):
    claim: str
    level: FactLevel
    evidence_refs: list[str] = Field(default_factory=list)


class EvidenceRef(ContractModel):
    evidence_id: str
    uri: str
    sha256: str | None = None
    fact_level: FactLevel = FactLevel.UNVERIFIED


class ErrorDetail(ContractModel):
    code: str
    message: str
    field: str | None = None
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ResultEnvelope(ContractModel):
    schema_version: str = "captcha-result/v1"
    operation_status: OperationStatus
    request_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: dict[str, Any] | None = None
    facts: list[FactClaim] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
