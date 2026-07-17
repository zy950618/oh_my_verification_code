from __future__ import annotations

import json
from pathlib import Path

from captcha_verification.contracts import (
    ActionPlan,
    AuthorizationRecord,
    BusinessAcceptanceReceipt,
    ClassificationRequest,
    ClassificationResult,
    PredictionOutcome,
    PromotionDecision,
    RegistryEntry,
    ResultEnvelope,
    SolveRequest,
)

MODELS = [
    AuthorizationRecord,
    ClassificationRequest,
    ClassificationResult,
    SolveRequest,
    PredictionOutcome,
    ActionPlan,
    BusinessAcceptanceReceipt,
    PromotionDecision,
    RegistryEntry,
    ResultEnvelope,
]


def export_schemas(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for model in MODELS:
        name = model.model_fields["schema_version"].default.replace("/", "-")
        path = output_dir / f"{name}.schema.json"
        path.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written
