from __future__ import annotations

import importlib
from collections.abc import Iterable

from captcha_verification.contracts import RegistryEntry


class Registry:
    def __init__(self, entries: Iterable[RegistryEntry] = ()) -> None:
        self._entries: dict[tuple[str, str, str], RegistryEntry] = {}
        for entry in entries:
            self.register(entry)

    def register(self, entry: RegistryEntry) -> None:
        key = (entry.entry_type, entry.entry_id, entry.version)
        if key in self._entries:
            raise ValueError(f"duplicate registry entry: {key}")
        self._entries[key] = entry

    def list(self, entry_type: str | None = None) -> list[RegistryEntry]:
        entries = self._entries.values()
        if entry_type:
            entries = (entry for entry in entries if entry.entry_type == entry_type)
        return sorted(entries, key=lambda item: (item.entry_type, item.entry_id, item.version))

    def get(self, entry_type: str, entry_id: str, version: str | None = None) -> RegistryEntry:
        candidates = [
            entry
            for (kind, identifier, _), entry in self._entries.items()
            if kind == entry_type and identifier == entry_id and (version is None or entry.version == version)
        ]
        if not candidates:
            raise KeyError(f"unknown registry entry: {(entry_type, entry_id, version)}")
        if version is None:
            active = [entry for entry in candidates if entry.lifecycle_state == "active"]
            candidates = active or candidates
        return sorted(candidates, key=lambda item: item.version)[-1]

    def validate_imports(self) -> list[str]:
        errors: list[str] = []
        for entry in self._entries.values():
            if not entry.import_path:
                continue
            module_name, separator, attribute = entry.import_path.partition(":")
            if not separator:
                errors.append(f"{entry.entry_id}: import_path must use module:attribute")
                continue
            try:
                module = importlib.import_module(module_name)
                value = getattr(module, attribute)
                if not callable(value):
                    errors.append(f"{entry.entry_id}: import target is not callable")
            except (ImportError, AttributeError) as exc:
                errors.append(f"{entry.entry_id}: {exc}")
        return errors


DEFAULT_REGISTRY = Registry()
