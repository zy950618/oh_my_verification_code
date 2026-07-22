from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .contracts import PromptPackManifest
from .policy import restricted_terms, safe_path


@dataclass(frozen=True)
class PromptChange:
    source: str
    destination: str
    operation: str
    source_hash: str
    destination_hash: str | None
    restricted: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return self.__dict__ | {"restricted": list(self.restricted)}


@dataclass(frozen=True)
class PromptInstallPlan:
    manifest: PromptPackManifest
    changes: tuple[PromptChange, ...]
    source_root: Path
    destination_root: Path

    @property
    def restricted(self) -> bool:
        return self.manifest.restricted_prompt_pack or any(change.restricted for change in self.changes)

    def to_dict(self) -> dict[str, object]:
        return {"manifest": self.manifest.model_dump(mode="json"), "changes": [c.to_dict() for c in self.changes], "restricted": self.restricted}


class PromptPackInstaller:
    def __init__(self, *, allowed_destination_roots: tuple[Path, ...], ledger_path: Path) -> None:
        self.allowed_destination_roots = allowed_destination_roots
        self.ledger_path = ledger_path

    def inspect(self, source: Path, destination: Path) -> PromptInstallPlan:
        source_root, manifest = self._read_source(source)
        destination = safe_path(destination, self.allowed_destination_roots)
        changes: list[PromptChange] = []
        for source_file in sorted(source_root.rglob("*")):
            if not source_file.is_file() or source_file.name == "manifest.json":
                continue
            relative = source_file.relative_to(source_root)
            target = safe_path(destination / relative, self.allowed_destination_roots)
            source_hash = hashlib.sha256(source_file.read_bytes()).hexdigest()
            target_hash = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
            terms = tuple(restricted_terms(source_file.read_text(encoding="utf-8", errors="replace")))
            changes.append(PromptChange(str(relative), str(relative), "skip" if source_hash == target_hash else "update" if target.exists() else "create", source_hash, target_hash, terms))
        return PromptInstallPlan(manifest=manifest, changes=tuple(changes), source_root=source_root, destination_root=destination)

    def dry_run(self, plan: PromptInstallPlan) -> dict[str, object]:
        return {"operation": "dry_run", "plan": plan.to_dict(), "would_write": any(c.operation != "skip" for c in plan.changes)}

    def apply(self, plan: PromptInstallPlan, *, evaluation_profile: bool = False) -> dict[str, object]:
        if plan.restricted and not evaluation_profile:
            return {"status": "blocked", "reason": "restricted_prompt_pack", "findings": sorted({term for change in plan.changes for term in change.restricted})}
        backup_id = uuid4().hex
        backups: list[dict[str, object]] = []
        plan.destination_root.mkdir(parents=True, exist_ok=True)
        for change in plan.changes:
            if change.operation == "skip":
                continue
            source_file = plan.source_root / change.source
            target = safe_path(plan.destination_root / change.destination, self.allowed_destination_roots)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                backup = plan.destination_root / f".prompt-backup-{backup_id}" / change.destination
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                backups.append({"target": str(target), "backup": str(backup), "hash": change.destination_hash})
            with tempfile.NamedTemporaryFile("wb", dir=target.parent, delete=False) as handle:
                handle.write(source_file.read_bytes())
                temporary = Path(handle.name)
            os.replace(temporary, target)
        ledger = self._load_ledger()
        record = {"backup_id": backup_id, "pack_id": plan.manifest.pack_id, "destination_root": str(plan.destination_root), "backups": backups, "changes": [c.to_dict() for c in plan.changes]}
        ledger.append(record)
        self._save_ledger(ledger)
        return {"status": "applied", "backup_id": backup_id, "record": record}

    def rollback(self, backup_id: str) -> dict[str, object]:
        ledger = self._load_ledger()
        record = next((item for item in ledger if item.get("backup_id") == backup_id), None)
        if record is None:
            raise ValueError("unknown prompt backup revision")
        for item in record.get("backups", []):
            target = safe_path(Path(item["target"]), self.allowed_destination_roots)
            backup = Path(item["backup"])
            if not backup.exists():
                raise ValueError("prompt backup is missing")
            os.replace(backup, target)
        return {"status": "rolled_back", "backup_id": backup_id}

    def _read_source(self, source: Path) -> tuple[Path, PromptPackManifest]:
        temporary: Path | None = None
        if source.is_file() and source.suffix.lower() == ".zip":
            temporary = Path(tempfile.mkdtemp(prefix="prompt-pack-"))
            with zipfile.ZipFile(source) as archive:
                for name in archive.namelist():
                    member = Path(name)
                    if member.is_absolute() or ".." in member.parts:
                        raise ValueError("prompt archive path traversal")
                archive.extractall(temporary)
            source = temporary
        if not source.is_dir():
            raise ValueError("prompt pack source must be a directory or zip")
        manifest_path = source / "manifest.json"
        if not manifest_path.exists():
            raise ValueError("prompt pack manifest.json is required")
        manifest = PromptPackManifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
        content = b"".join(path.read_bytes() for path in sorted(source.rglob("*")) if path.is_file() and path.name != "manifest.json")
        if hashlib.sha256(content).hexdigest() != manifest.content_hash:
            raise ValueError("prompt pack content hash mismatch")
        return source, manifest

    def _load_ledger(self) -> list[dict[str, object]]:
        if not self.ledger_path.exists():
            return []
        return json.loads(self.ledger_path.read_text(encoding="utf-8"))

    def _save_ledger(self, ledger: list[dict[str, object]]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
