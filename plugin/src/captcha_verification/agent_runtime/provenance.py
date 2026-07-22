from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from captcha_verification.canonical import artifact_hash, file_sha256

from .contracts import FactLevel


class ProvenanceRecord:
    """Small append-only provenance record kept deliberately independent of workers."""

    def __init__(
        self,
        *,
        artifact_id: str,
        artifact_type: str,
        sha256: str,
        path: str | None = None,
        parent_ids: Iterable[str] = (),
        scope: str = "offline_compute",
        fact_level: FactLevel = "observed",
        evidence_stage: str = "E1_static_validated",
        freshness: str = "current",
        revision: int = 1,
        status: str = "active",
        missing_evidence: Iterable[str] = (),
        secret_detected: bool = False,
        network_accessed: bool = False,
    ) -> None:
        self.artifact_id = artifact_id
        self.artifact_type = artifact_type
        self.path = path
        self.sha256 = sha256
        self.parent_ids = sorted(parent_ids)
        self.scope = scope
        self.fact_level = fact_level
        self.evidence_stage = evidence_stage
        self.freshness = freshness
        self.revision = revision
        self.status = status
        self.missing_evidence = sorted(missing_evidence)
        self.secret_detected = secret_detected
        self.network_accessed = network_accessed

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "path": self.path,
            "sha256": self.sha256,
            "parent_ids": self.parent_ids,
            "scope": self.scope,
            "fact_level": self.fact_level,
            "evidence_stage": self.evidence_stage,
            "freshness": self.freshness,
            "revision": self.revision,
            "status": self.status,
            "missing_evidence": self.missing_evidence,
            "secret_detected": self.secret_detected,
            "network_accessed": self.network_accessed,
        }

    @property
    def canonical_hash(self) -> str:
        return artifact_hash(self.to_dict())


class ProvenanceRegistry:
    def __init__(self, records: Iterable[ProvenanceRecord] = ()) -> None:
        self.records = list(records)

    def register(self, record: ProvenanceRecord) -> ProvenanceRecord:
        if record.secret_detected:
            raise ValueError("secret-bearing artifacts cannot enter provenance registry")
        if any(existing.artifact_id == record.artifact_id and existing.revision == record.revision for existing in self.records):
            raise ValueError("duplicate provenance revision")
        self.records.append(record)
        return record

    def list(self, *, artifact_type: str | None = None, status: str | None = None) -> list[ProvenanceRecord]:
        return [r for r in self.records if (artifact_type is None or r.artifact_type == artifact_type) and (status is None or r.status == status)]

    def verify(self) -> list[str]:
        errors: list[str] = []
        seen: set[str] = set()
        for record in self.records:
            if record.canonical_hash in seen:
                errors.append(f"duplicate canonical record: {record.artifact_id}")
            seen.add(record.canonical_hash)
            if record.secret_detected:
                errors.append(f"secret detected: {record.artifact_id}")
            if record.path and Path(record.path).exists() and file_sha256(Path(record.path)) != record.sha256:
                errors.append(f"sha256 mismatch: {record.artifact_id}")
        return errors

    def to_dict(self) -> dict[str, object]:
        return {"manifest_type": "provenance_registry", "records": [record.to_dict() | {"canonical_hash": record.canonical_hash} for record in self.records]}

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ProvenanceRegistry":
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = []
        for item in payload.get("records", []):
            value = dict(item)
            value.pop("canonical_hash", None)
            records.append(ProvenanceRecord(**value))
        return cls(records)
