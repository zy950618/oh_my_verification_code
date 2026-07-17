from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator


IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEMPLATE_VERSION = "target-adapter/v1"
GENERATOR_VERSION = "1.0.0"


class ScaffoldSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    challenge_family: str
    transports: list[str] = Field(default_factory=lambda: ["cli"])

    @field_validator("target_id", "challenge_family")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not IDENTIFIER.fullmatch(value):
            raise ValueError("must be lowercase kebab-case")
        return value

    @field_validator("transports")
    @classmethod
    def validate_transports(cls, values: list[str]) -> list[str]:
        allowed = {"cli", "fastapi", "mcp"}
        normalized = sorted(set(values))
        if not normalized or set(normalized) - allowed:
            raise ValueError(f"transports must be a non-empty subset of {sorted(allowed)}")
        return normalized


@dataclass(frozen=True)
class GeneratedFile:
    path: str
    content: str
    sha256: str


@dataclass(frozen=True)
class ScaffoldResult:
    status: str
    adapter_id: str
    target_id: str
    template_version: str
    generator_version: str
    request_hash: str
    output_root: str
    files: tuple[GeneratedFile, ...]
    missing_evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "adapter_id": self.adapter_id,
            "target_id": self.target_id,
            "template_version": self.template_version,
            "generator_version": self.generator_version,
            "request_hash": self.request_hash,
            "output_root": self.output_root,
            "files": [file.__dict__ for file in self.files],
            "missing_evidence": list(self.missing_evidence),
            "execution_status": "not_run",
        }


def _class_name(target_id: str) -> str:
    return "".join(part.title() for part in target_id.split("-"))


def _render(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace("{{ " + key + " }}", value)
    unresolved = re.findall(r"\{\{\s*[^}]+\s*}}", rendered)
    if unresolved:
        raise ValueError(f"unresolved template variables: {unresolved}")
    return rendered


def _safe_output_root(root: Path, target_id: str) -> Path:
    resolved = root.resolve()
    if resolved.name != target_id:
        raise ValueError("output root must end in the target ID")
    if resolved.parent.name != "targets" or resolved.parent.parent.name != "private":
        raise ValueError("target adapters must be generated under private/targets/<target-id>")
    return resolved


def build_scaffold(spec: ScaffoldSpec, *, template_root: Path, output_root: Path) -> ScaffoldResult:
    target_root = _safe_output_root(output_root, spec.target_id)
    adapter_id = f"{spec.target_id}-{spec.challenge_family}"
    replacements = {
        "adapter_id": adapter_id,
        "target_id": spec.target_id,
        "challenge_family": spec.challenge_family,
        "transports_json": json.dumps(spec.transports),
        "class_name": _class_name(spec.target_id),
    }
    layout = {
        "target.yaml": "target.yaml.tpl",
        "authorization.example.yaml": "authorization.example.yaml.tpl",
        "adapter.py": "adapter.py.tpl",
        "tests/test_adapter.py": "test_adapter.py.tpl",
        "README.md": "README.md.tpl",
    }
    files: list[GeneratedFile] = []
    for destination, source in layout.items():
        template = (template_root / source).read_text(encoding="utf-8")
        content = _render(template, replacements)
        files.append(GeneratedFile(destination, content, hashlib.sha256(content.encode()).hexdigest()))

    request_payload = spec.model_dump(mode="json")
    request_hash = hashlib.sha256(json.dumps(request_payload, sort_keys=True).encode()).hexdigest()
    manifest = {
        "schema_version": "captcha-scaffold-manifest/v1",
        "template_version": TEMPLATE_VERSION,
        "generator_version": GENERATOR_VERSION,
        "request_hash": request_hash,
        "adapter_id": adapter_id,
        "target_id": spec.target_id,
        "visibility": "private",
        "status": "generated_not_executed",
        "generated_files": [{"path": file.path, "sha256": file.sha256} for file in files],
        "missing_evidence": [
            "verified authorization record",
            "observed provider binding",
            "first-party business acceptance assertions",
        ],
    }
    manifest_content = json.dumps(manifest, indent=2) + "\n"
    files.append(GeneratedFile("scaffold-manifest.json", manifest_content, hashlib.sha256(manifest_content.encode()).hexdigest()))
    return ScaffoldResult(
        status="generated_not_executed",
        adapter_id=adapter_id,
        target_id=spec.target_id,
        template_version=TEMPLATE_VERSION,
        generator_version=GENERATOR_VERSION,
        request_hash=request_hash,
        output_root=str(target_root),
        files=tuple(files),
        missing_evidence=tuple(manifest["missing_evidence"]),
    )


def write_scaffold(result: ScaffoldResult) -> list[Path]:
    root = Path(result.output_root)
    written: list[Path] = []
    for file in result.files:
        path = (root / file.path).resolve()
        if root not in path.parents:
            raise ValueError(f"generated path escapes output root: {file.path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file.content, encoding="utf-8")
        written.append(path)
    return written
