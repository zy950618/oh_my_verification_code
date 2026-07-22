from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .artifacts import ArtifactBinding
from .common import ContractModel, EvidenceRef, FactClaim
from .enums import BusinessAcceptanceStatus, ChallengeFamily, PredictionStatus, SolutionType


class Point(ContractModel):
    x: float
    y: float


class Offset(ContractModel):
    x: float
    y: float = 0


class TrackPoint(Point):
    time_ms: int = Field(ge=0)


class Press(ContractModel):
    duration_ms: int = Field(gt=0, le=30_000)
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
        if not present[SolutionType(self.type)]:
            raise ValueError(f"solution payload for {self.type!s} is required")
        return self


class AssetRef(ContractModel):
    asset_id: str
    uri: str
    media_type: str
    sha256: str
    width_px: int | None = Field(default=None, gt=0)
    height_px: int | None = Field(default=None, gt=0)


class ClassificationRequest(ContractModel):
    schema_version: str = "captcha-classification-request/v1"
    request_id: str
    assets: list[AssetRef]
    context: dict[str, Any] = Field(default_factory=dict)
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
    challenge_family: ChallengeFamily
    confidence: float = Field(ge=0, le=1)
    required_solver_capability: str
    authorization_decision: str
    classifier_version: str
    classifier_hash: str
    input_hash: str
    classifier_binding: ArtifactBinding | None = None
    status: PredictionStatus = PredictionStatus.PRODUCED
    evidence: list[EvidenceRef] = Field(default_factory=list)
    facts: list[FactClaim] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_family_status(self) -> "ClassificationResult":
        family = ChallengeFamily(self.challenge_family)
        status = PredictionStatus(self.status)
        if status in {PredictionStatus.UNSUPPORTED, PredictionStatus.FAILED} and self.confidence != 0:
            raise ValueError("unsupported or failed classification must use zero confidence")
        if family == ChallengeFamily.UNKNOWN and status == PredictionStatus.PRODUCED:
            raise ValueError("unknown classification cannot be produced")
        if status == PredictionStatus.PRODUCED and self.confidence <= 0:
            raise ValueError("produced classification requires positive confidence")
        return self


class SolveRequest(ContractModel):
    schema_version: str = "captcha-solve-request/v1"
    request_id: str
    challenge_instance_id: str
    challenge_family: ChallengeFamily
    assets: list[AssetRef]
    allowed_solution_types: list[SolutionType]
    classification_id: str | None = None
    classification_hash: str | None = None
    classification_confidence: float | None = Field(default=None, ge=0, le=1)
    solver_id: str | None = None
    authorization_record_id: str | None = None
    expires_at: datetime | None = None


    @model_validator(mode="after")
    def validate_request(self) -> "SolveRequest":
        if not self.allowed_solution_types:
            raise ValueError("allowed_solution_types must not be empty")
        if self.expires_at is not None and self.expires_at <= datetime.now(self.expires_at.tzinfo):
            raise ValueError("solve request has expired")
        return self


class PredictionOutcome(ContractModel):
    schema_version: str = "captcha-prediction/v1"
    prediction_id: str
    request_id: str
    challenge_instance_id: str
    status: PredictionStatus
    solution: NormalizedSolution | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    calibration_version: str | None = None
    calibration_hash: str | None = None
    solver_id: str | None = None
    solver_version: str | None = None
    model_id: str | None = None
    dataset_version: str | None = None
    preprocessing_version: str | None = None
    input_hash: str | None = None
    classification_hash: str | None = None
    artifact_hash: str | None = None
    bindings: list[ArtifactBinding] = Field(default_factory=list)
    latency_ms: float | None = Field(default=None, ge=0)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    facts: list[FactClaim] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    business_acceptance_status: Literal[BusinessAcceptanceStatus.NOT_ATTEMPTED] = BusinessAcceptanceStatus.NOT_ATTEMPTED

    @model_validator(mode="after")
    def enforce_prediction_payload(self) -> "PredictionOutcome":
        status = PredictionStatus(self.status)
        if status == PredictionStatus.PRODUCED:
            if self.solution is None or self.confidence is None:
                raise ValueError("produced predictions require solution and confidence")
            if self.confidence <= 0:
                raise ValueError("produced predictions require positive confidence")
            if not self.solver_id or not self.solver_version or not self.input_hash:
                raise ValueError("produced predictions require solver identity and input hash")
            if not self.calibration_version or not self.calibration_hash:
                raise ValueError("produced predictions require calibration identity")
        elif self.solution is not None:
            raise ValueError("non-produced predictions must not include a solution")
        return self
