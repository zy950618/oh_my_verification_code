from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from captcha_verification.canonical import artifact_hash

from .artifacts import ArtifactBinding
from .common import ContractModel


class RegistryEntry(ContractModel):
    schema_version: str = "captcha-registry-entry/v1"
    entry_type: Literal["classifier", "solver", "model", "dataset", "action", "target", "evidence"]
    entry_id: str
    version: str
    lifecycle_state: Literal["experimental", "candidate", "active", "deprecated", "disabled"]
    capabilities: list[str]
    supported_challenge_families: list[str] = Field(default_factory=list)
    input_schema: str
    output_schema: str
    import_path: str | None = None
    artifact_uri: str | None = None
    sha256: str | None = None
    latency_class: Literal["interactive", "standard", "batch"] = "standard"
    concurrency_safe: bool = False
    authorization_scopes: list[str] = Field(default_factory=list)
    deprecated_by: str | None = None
    health_status: Literal["unknown", "ready", "failed"] = "unknown"
    runtime_eligibility: Literal["positive_local_reference", "negative_eval_only", "documentation_only"] = "documentation_only"

    @model_validator(mode="after")
    def enforce_active_artifact_identity(self) -> "RegistryEntry":
        if self.lifecycle_state == "active" and self.runtime_eligibility == "positive_local_reference":
            if not self.sha256:
                raise ValueError("active local-reference registry entries require sha256")
            if self.entry_type in {"classifier", "solver", "action"} and not self.import_path:
                raise ValueError("active executable registry entries require import_path")
        return self

    def binding(self) -> ArtifactBinding:
        value = self.sha256 or artifact_hash(
            {
                "entry_type": self.entry_type,
                "entry_id": self.entry_id,
                "version": self.version,
                "capabilities": self.capabilities,
                "runtime_eligibility": self.runtime_eligibility,
            }
        )
        return ArtifactBinding(
            registry_kind=self.entry_type,
            entry_id=self.entry_id,
            version=self.version,
            artifact_hash=value,
        )
