from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import ContractModel


class RegistryEntry(ContractModel):
    schema_version: str = "captcha-registry-entry/v1"
    entry_type: Literal["solver", "model", "dataset", "action", "target"]
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
