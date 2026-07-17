from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .common import ContractModel, EvidenceRef, FactClaim
from .enums import BusinessAcceptanceStatus, PredictionStatus, SolutionType


class Point(ContractModel):
    x: float
    y: float


class Offset(ContractModel):
    x: float
    y: float = 0


class TrackPoint(Point):
    time_ms: int = Field(ge=0)


class Press(ContractModel):
    duration_ms: int = Field(gt=0)
    x: float | None = None
    y: float | None = None


class NormalizedSolution(ContractModel):
    type: SolutionType
    text: str | None = None
    points: list[Point] = Field(default_factory=list)
    tiles: list[int] = Field(default_factory=list)
    offset: Offset | None = None
    angle_degrees: float | None = None
    track: list[TrackPoint] = Field(default_factory=list)
    press: Press | None = None

    @model_validator(mode="after")
    def require_matching_payload(self) -> "NormalizedSolution":
        present = {
            SolutionType.TEXT: bool(self.text),
            SolutionType.POINTS: bool(self.points),
            SolutionType.TILES: bool(self.tiles),
            SolutionType.OFFSET: self.offset is not None,
            SolutionType.ANGLE: self.angle_degrees is not None,
            SolutionType.TRACK: bool(self.track),
            SolutionType.PRESS: self.press is not None,
        }
        if not present[self.type]:
            raise ValueError(f"solution payload for {self.type!s} is required")
        return self


class AssetRef(ContractModel):
    asset_id: str
    uri: str
    media_type: str
    sha256: str


class ClassificationRequest(ContractModel):
    schema_version: str = "captcha-classification-request/v1"
    request_id: str
    assets: list[AssetRef]
    context: dict[str, str] = Field(default_factory=dict)
    authorization_record_id: str | None = None


class ProviderCandidate(ContractModel):
    provider: str
    confidence: float = Field(ge=0, le=1)
    markers: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ClassificationResult(ContractModel):
    schema_version: str = "captcha-classification/v1"
    classification_id: str
    provider_candidates: list[ProviderCandidate]
    challenge_family: str
    confidence: float = Field(ge=0, le=1)
    required_solver_capability: str
    authorization_decision: str
    classifier_version: str
    facts: list[FactClaim] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SolveRequest(ContractModel):
    schema_version: str = "captcha-solve-request/v1"
    request_id: str
    challenge_instance_id: str
    challenge_family: str
    assets: list[AssetRef]
    allowed_solution_types: list[SolutionType]
    classification_id: str | None = None
    solver_id: str | None = None
    authorization_record_id: str | None = None


class PredictionOutcome(ContractModel):
    schema_version: str = "captcha-prediction/v1"
    prediction_id: str
    request_id: str
    challenge_instance_id: str
    status: PredictionStatus
    solution: NormalizedSolution | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    calibration_version: str | None = None
    solver_id: str | None = None
    solver_version: str | None = None
    model_id: str | None = None
    dataset_version: str | None = None
    preprocessing_version: str | None = None
    input_hash: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    facts: list[FactClaim] = Field(default_factory=list)
    business_acceptance_status: Literal[BusinessAcceptanceStatus.NOT_ATTEMPTED] = BusinessAcceptanceStatus.NOT_ATTEMPTED

    @model_validator(mode="after")
    def enforce_prediction_payload(self) -> "PredictionOutcome":
        if self.status == PredictionStatus.PRODUCED:
            if self.solution is None or self.confidence is None:
                raise ValueError("produced predictions require solution and confidence")
            if not self.solver_id or not self.solver_version or not self.input_hash:
                raise ValueError("produced predictions require solver identity and input hash")
        elif self.solution is not None:
            raise ValueError("non-produced predictions must not include a solution")
        return self
