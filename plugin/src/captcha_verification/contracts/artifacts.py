from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from captcha_verification.canonical import artifact_hash

from .common import ContractModel


class ArtifactBinding(ContractModel):
    registry_kind: Literal["classifier", "solver", "model", "dataset", "action", "target", "evidence"]
    entry_id: str
    version: str
    artifact_hash: str


class CalibrationBin(ContractModel):
    minimum_score: float = Field(ge=0, le=1)
    maximum_score: float = Field(ge=0, le=1)
    samples: int = Field(ge=1)
    successes: int = Field(ge=0)
    calibrated_confidence: float = Field(ge=0, le=1)
    wilson_lower_bound: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_bin(self) -> "CalibrationBin":
        if self.maximum_score <= self.minimum_score:
            raise ValueError("maximum_score must be greater than minimum_score")
        if self.successes > self.samples:
            raise ValueError("successes cannot exceed samples")
        return self


class CalibrationArtifact(ContractModel):
    schema_version: str = "captcha-calibration/v1"
    calibration_id: str
    family: str
    solver_binding: ArtifactBinding
    dataset_binding: ArtifactBinding
    preprocessing_version: str
    preprocessing_hash: str
    bins: list[CalibrationBin]
    artifact_hash: str | None = None

    @model_validator(mode="after")
    def validate_hash(self) -> "CalibrationArtifact":
        expected = artifact_hash(self)
        if self.artifact_hash is None:
            self.artifact_hash = expected
        elif self.artifact_hash != expected:
            raise ValueError("calibration artifact hash does not match content")
        return self
