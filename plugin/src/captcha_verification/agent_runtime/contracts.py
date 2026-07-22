from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ScopeTarget = Literal["offline_compute", "localhost_lab", "owned_authorized", "observation_only"]
AuthorizationStatus = Literal["not_applicable", "claimed_unverified", "verified", "expired", "revoked"]
FactLevel = Literal["observed", "derived", "assumed", "unverified"]


class Scope(BaseModel):
    repository: str | None = None
    target_environment: ScopeTarget = "offline_compute"
    authorization_status: AuthorizationStatus = "not_applicable"
    authorization_evidence: list[str] = Field(default_factory=list)
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_roots: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_authorization(self) -> "Scope":
        if self.authorization_status == "verified" and not self.authorization_evidence:
            raise ValueError("verified scope requires authorization evidence")
        if self.authorization_status in {"expired", "revoked"}:
            raise ValueError("expired or revoked authorization cannot be used")
        return self


class ResourceLimits(BaseModel):
    max_attempts: int = Field(default=1, ge=1, le=100)
    max_iterations: int = Field(default=3, ge=1, le=100)
    max_seconds: int = Field(default=300, ge=1, le=86_400)
    max_output_bytes: int = Field(default=1_000_000, ge=1, le=50_000_000)
    max_artifact_bytes: int = Field(default=10_000_000, ge=1, le=100_000_000)
    max_artifacts: int = Field(default=100, ge=1, le=10_000)


class SandboxProfile(BaseModel):
    name: Literal["read_only_repo", "offline_compute", "localhost_lab", "sandbox_replay", "owned_authorized", "observation_only"] = "offline_compute"
    network: Literal["none", "localhost_only", "allowlisted"] = "none"
    allowed_hosts: list[str] = Field(default_factory=list)
    browser: bool = False
    credentials: bool = False
    write_roots: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_network(self) -> "SandboxProfile":
        if self.network == "none" and self.allowed_hosts:
            raise ValueError("network=none cannot have allowed hosts")
        if self.network == "allowlisted" and not self.allowed_hosts:
            raise ValueError("allowlisted network requires allowed hosts")
        if self.credentials:
            raise ValueError("runtime profiles cannot expose credentials")
        return self


class AgentPolicyManifest(BaseModel):
    manifest_type: Literal["agent_policy"] = "agent_policy"
    policy_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    content_hash: str = Field(min_length=8)
    allowed_modes: list[str] = Field(default_factory=lambda: ["offline_compute", "localhost_lab"])
    forbidden_operations: list[str] = Field(default_factory=list)
    model_compatibility: list[str] = Field(default_factory=list)
    sandbox_profile: SandboxProfile = Field(default_factory=SandboxProfile)
    revision: int = Field(default=1, ge=1)


class AcceptanceCriteria(BaseModel):
    name: str = Field(min_length=1)
    required: bool = True
    evidence: list[str] = Field(default_factory=list)


class JobManifest(BaseModel):
    manifest_type: Literal["agent_job"] = "agent_job"
    job_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    scope: Scope = Field(default_factory=Scope)
    mode: ScopeTarget = "offline_compute"
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_operations: list[str] = Field(default_factory=list)
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)
    sandbox_profile: SandboxProfile = Field(default_factory=SandboxProfile)
    acceptance_criteria: list[str | AcceptanceCriteria] = Field(default_factory=list)
    policy_revision: str | None = None
    prompt_pack_id: str | None = None
    prompt_pack_hash: str | None = None
    input_artifacts: list[str] = Field(default_factory=list)
    run_label: str | None = None

    @model_validator(mode="after")
    def enforce_scope(self) -> "JobManifest":
        if self.mode != self.scope.target_environment:
            raise ValueError("job mode must match scope target_environment")
        if self.sandbox_profile.name != self.mode:
            raise ValueError("sandbox profile must match job mode")
        if self.mode == "owned_authorized" and self.scope.authorization_status != "verified":
            raise ValueError("owned_authorized jobs require verified authorization status")
        return self


class PromptPackManifest(BaseModel):
    manifest_type: Literal["prompt_pack"] = "prompt_pack"
    pack_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    content_hash: str = Field(min_length=8)
    model_compatibility: list[str] = Field(default_factory=list)
    allowed_scopes: list[ScopeTarget] = Field(default_factory=lambda: ["offline_compute", "localhost_lab"])
    tool_policy: list[str] = Field(default_factory=list)
    sandbox_profile: str = "offline_compute"
    test_bank: list[str] = Field(default_factory=list)
    rollback_revision: int | None = Field(default=None, ge=1)
    restricted_prompt_pack: bool = False


class AttemptRecord(BaseModel):
    attempt_id: str = Field(min_length=1)
    parent_attempt: str | None = None
    retry_reason: str | None = None
    fresh_challenge_or_session: bool = False
    budget_consumed: int = Field(default=0, ge=0)
    terminal_state: Literal["running", "completed", "blocked", "failed", "human_review_required"] = "running"


class ArtifactRecord(BaseModel):
    path: str = Field(min_length=1)
    role: str = Field(min_length=1)
    sha256: str = Field(min_length=8)
    sensitive: bool = False
    size_bytes: int | None = Field(default=None, ge=0)
    provenance_id: str | None = None


class BinaryExecutionReceipt(BaseModel):
    manifest_type: Literal["codex_binary_execution"] = "codex_binary_execution"
    run_id: str = Field(min_length=1)
    executable: str = Field(min_length=1)
    executable_sha256: str | None = None
    version_command: list[str] = Field(default_factory=list)
    version_output_hash: str | None = None
    help_output_hash: str | None = None
    command: list[str] = Field(default_factory=list)
    workspace: str = Field(min_length=1)
    environment_keys: list[str] = Field(default_factory=list)
    started_at: datetime
    ended_at: datetime
    exit_code: int | None = None
    stdout_hash: str = Field(min_length=8)
    stderr_hash: str = Field(min_length=8)
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    real_binary: bool = False
    fact_level: FactLevel = "observed"
    evidence_stage: str = "E1_static_validated"
    external_network_used: bool = False
    business_success: Literal["not_attempted", "not_verified", "accepted"] = "not_attempted"
    status: Literal["completed", "blocked", "failed"]
    missing_evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_boundaries(self) -> "BinaryExecutionReceipt":
        if self.business_success == "accepted":
            raise ValueError("Codex binary receipt cannot claim business acceptance")
        if self.external_network_used:
            raise ValueError("Codex binary receipt cannot claim external network use")
        if self.status == "completed" and not self.real_binary:
            raise ValueError("completed binary receipt must attest a real binary")
        if self.status == "completed" and self.evidence_stage != "E2_local_executed":
            raise ValueError("completed binary receipt requires local execution evidence")
        if self.ended_at < self.started_at:
            raise ValueError("ended_at must not precede started_at")
        return self


class ResultManifest(BaseModel):
    manifest_type: Literal["agent_result"] = "agent_result"
    job_id: str = Field(min_length=1)
    status: Literal["completed", "blocked", "failed", "human_review_required"]
    backend: str = Field(min_length=1)
    model: str | None = None
    input_hash: str = Field(min_length=8)
    output_hash: str = Field(min_length=8)
    prompt_hash: str | None = None
    config_hash: str | None = None
    environment_hash: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    test_results: list[dict[str, object]] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    tests_passed: int = Field(default=0, ge=0)
    tests_failed: int = Field(default=0, ge=0)
    review_status: Literal["not_reviewed", "accepted", "rejected", "needs_human_review", "unverified"] = "not_reviewed"
    evidence_stage: str = "E1_static_validated"
    fact_level: FactLevel = "unverified"
    missing_evidence: list[str] = Field(default_factory=list)
    business_success: Literal["not_attempted", "not_verified", "accepted"] = "not_attempted"
    reviewer_summary: str | None = None
    external_network_used: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def block_unverified_business_claim(self) -> "ResultManifest":
        if self.business_success == "accepted" and self.evidence_stage not in {"E5_authorized_business_accepted", "E6_repeat_verified"}:
            raise ValueError("business_success=accepted requires an authorized business evidence stage")
        if self.business_success == "accepted" and not self.artifacts:
            raise ValueError("business_success=accepted requires receipt evidence")
        if self.external_network_used and self.evidence_stage not in {"E5_authorized_business_accepted", "E6_repeat_verified"}:
            raise ValueError("external network use requires authorized evidence stage")
        return self


class RuntimePolicyDecision(BaseModel):
    allowed: bool
    job_id: str
    scope: ScopeTarget
    reason: str
    denied_reasons: list[str] = Field(default_factory=list)
    fact_level: FactLevel = "observed"
    network_allowed: bool = False
    external_generalization_allowed: bool = False


class PolicyReceipt(BaseModel):
    manifest_type: Literal["policy_receipt"] = "policy_receipt"
    receipt_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    policy_hash: str = Field(min_length=8)
    job_hash: str = Field(min_length=8)
    decision: RuntimePolicyDecision
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReviewVerdict(BaseModel):
    manifest_type: Literal["review_verdict"] = "review_verdict"
    job_id: str = Field(min_length=1)
    verdict: Literal["accepted", "rejected", "needs_human_review", "unverified"]
    findings: list[str] = Field(default_factory=list)
    evidence_paths: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    reviewer: str = Field(min_length=1)
    reviewer_hash: str = Field(min_length=8)
    overclaim_detected: bool = False
    secret_leak_detected: bool = False
    scope_violation_detected: bool = False
    positive_claim_allowed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
