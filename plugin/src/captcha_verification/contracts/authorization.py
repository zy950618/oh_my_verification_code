from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator

from .common import ContractModel, EvidenceRef
from .enums import AuthorizationBasis, AuthorizationStatus, FactLevel


class AuthorizationRecord(ContractModel):
    schema_version: str = "captcha-authorization/v1"
    authorization_id: str
    subject: str
    controller: str
    target_environment_id: str
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_routes: list[str] = Field(default_factory=list)
    allowed_methods: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    prohibited_actions: list[str] = Field(default_factory=list)
    basis: AuthorizationBasis
    status: AuthorizationStatus
    fact_level: FactLevel
    evidence: list[EvidenceRef] = Field(default_factory=list)
    issued_at: datetime
    expires_at: datetime
    revocation_contact: str
    data_handling_scope: str
    production_allowed: bool = False
    operator_acknowledged: bool = False

    @field_validator("allowed_hosts")
    @classmethod
    def normalize_hosts(cls, hosts: list[str]) -> list[str]:
        normalized: list[str] = []
        for host in hosts:
            value = host.strip().lower().rstrip(".")
            if "://" in value:
                value = urlparse(value).hostname or ""
            if not value or "/" in value or value.startswith("."):
                raise ValueError(f"invalid allowed host: {host!r}")
            normalized.append(value)
        return sorted(set(normalized))

    @field_validator("allowed_methods")
    @classmethod
    def normalize_methods(cls, methods: list[str]) -> list[str]:
        allowed = {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}
        normalized = sorted({method.upper() for method in methods})
        unknown = set(normalized) - allowed
        if unknown:
            raise ValueError(f"unsupported HTTP methods: {sorted(unknown)}")
        return normalized

    @model_validator(mode="after")
    def enforce_authorization_invariants(self) -> "AuthorizationRecord":
        now = datetime.now(timezone.utc)
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be later than issued_at")
        if self.expires_at <= now and self.status not in {
            AuthorizationStatus.EXPIRED,
            AuthorizationStatus.REVOKED,
            AuthorizationStatus.REJECTED,
        }:
            raise ValueError("expired records must use an expired or terminal status")
        if self.basis == AuthorizationBasis.ORAL_CLAIM:
            if self.status != AuthorizationStatus.CLAIMED_UNVERIFIED:
                raise ValueError("oral claims must remain claimed_unverified")
            if self.fact_level != FactLevel.UNVERIFIED:
                raise ValueError("oral claims must remain unverified")
            if self.production_allowed:
                raise ValueError("oral claims cannot enable production execution")
        if self.status == AuthorizationStatus.VERIFIED:
            if self.fact_level != FactLevel.OBSERVED:
                raise ValueError("verified authorization requires observed evidence")
            if not self.evidence:
                raise ValueError("verified authorization requires evidence")
        return self

    def allows(self, *, host: str, route: str, method: str, action: str, now: datetime | None = None) -> bool:
        at = now or datetime.now(timezone.utc)
        hostname = (urlparse(host).hostname if "://" in host else host).lower().rstrip(".")
        return (
            self.status == AuthorizationStatus.VERIFIED
            and self.fact_level == FactLevel.OBSERVED
            and self.issued_at <= at < self.expires_at
            and hostname in self.allowed_hosts
            and route in self.allowed_routes
            and method.upper() in self.allowed_methods
            and action in self.allowed_actions
            and action not in self.prohibited_actions
            and self.operator_acknowledged
        )
