from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


_SELF_HASH_FIELDS = {
    "ActionPlan": "plan_hash",
    "CalibrationArtifact": "artifact_hash",
    "BusinessAcceptanceReceipt": "receipt_hash",
    "ExecutionReceipt": "receipt_hash",
    "PredictionOutcome": "artifact_hash",
    "ProviderVerificationReceipt": "receipt_hash",
}


def _json_value(value: Any, *, root: bool = False) -> Any:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude_none=False)
        if root:
            field = _SELF_HASH_FIELDS.get(type(value).__name__)
            if field:
                payload.pop(field, None)
        return {str(key): _json_value(child) for key, child in payload.items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(child) for child in value]
    return value


def canonical_json(value: Any) -> bytes:
    """Serialize an artifact deterministically, excluding only its own hash field."""
    return json.dumps(_json_value(value, root=True), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def artifact_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
