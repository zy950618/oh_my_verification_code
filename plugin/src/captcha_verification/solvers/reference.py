from __future__ import annotations

import math
import uuid
from dataclasses import dataclass

from captcha_verification.canonical import artifact_hash
from captcha_verification.contracts import (
    ArtifactBinding,
    ChallengeFamily,
    EvidenceRef,
    FactClaim,
    FactLevel,
    NormalizedSolution,
    Offset,
    Point,
    PredictionOutcome,
    PredictionStatus,
    SolutionType,
    SolveRequest,
)
from captcha_verification.raster import Raster, bright_mask, load_raster, mask_components, red_mask


DATASET_VERSION = "reference-synthetic-raster-v1"
DATASET_HASH = artifact_hash({"generator": "reference-fixtures-v1", "families": ["slider", "rotate", "click"]})
MODEL_ID = "reference-raster-algorithms"
MODEL_VERSION = "1.0.0"
MODEL_HASH = artifact_hash({"id": MODEL_ID, "weights": False, "families": ["slider", "rotate", "click"]})
PREPROCESSING_VERSION = "rgb-explicit-v1"
PREPROCESSING_HASH = artifact_hash({"mode": "RGB", "orientation": "explicit", "resize": "none"})
CALIBRATION_VERSION = "reference-calibration-v1"
CALIBRATION_HASHES = {
    family: artifact_hash({"version": CALIBRATION_VERSION, "family": family, "method": "conservative-quality-bins-v1"})
    for family in ("slider", "rotate", "click")
}


def _calibrate(family: str, raw: float) -> float:
    if raw < 0.45:
        return 0.25
    if raw < 0.65:
        return 0.55
    if raw < 0.8:
        return 0.72
    return 0.9


def _bindings(solver_id: str, solver_version: str) -> list[ArtifactBinding]:
    return [
        ArtifactBinding(registry_kind="solver", entry_id=solver_id, version=solver_version, artifact_hash=artifact_hash({"id": solver_id, "version": solver_version})),
        ArtifactBinding(registry_kind="model", entry_id=MODEL_ID, version=MODEL_VERSION, artifact_hash=MODEL_HASH),
        ArtifactBinding(registry_kind="dataset", entry_id="reference-synthetic-raster", version=DATASET_VERSION, artifact_hash=DATASET_HASH),
    ]


def _outcome(
    request: SolveRequest,
    *,
    solver_id: str,
    solver_version: str,
    raster: Raster | None,
    status: PredictionStatus,
    solution: NormalizedSolution | None = None,
    confidence: float | None = None,
    warning: str | None = None,
) -> PredictionOutcome:
    input_hash = raster.sha256 if raster else artifact_hash([asset.sha256 for asset in request.assets])
    payload = {
        "request_id": request.request_id,
        "challenge_instance_id": request.challenge_instance_id,
        "solver_id": solver_id,
        "solver_version": solver_version,
        "input_hash": input_hash,
        "status": status.value,
        "solution": solution.model_dump(mode="json") if solution else None,
        "confidence": confidence,
    }
    evidence = [
        EvidenceRef(evidence_id="solver-input", uri=request.assets[0].uri, sha256=input_hash, fact_level=FactLevel.OBSERVED),
        EvidenceRef(evidence_id="solver-decision", uri="memory://reference-solver/decision", sha256=artifact_hash(payload), fact_level=FactLevel.DERIVED),
    ]
    return PredictionOutcome(
        prediction_id=f"prediction-{uuid.uuid5(uuid.NAMESPACE_URL, artifact_hash(payload))}",
        request_id=request.request_id,
        challenge_instance_id=request.challenge_instance_id,
        status=status,
        solution=solution,
        confidence=confidence,
        calibration_version=CALIBRATION_VERSION if status == PredictionStatus.PRODUCED else None,
        calibration_hash=CALIBRATION_HASHES.get(ChallengeFamily(request.challenge_family).value) if status == PredictionStatus.PRODUCED else None,
        solver_id=solver_id,
        solver_version=solver_version,
        model_id=MODEL_ID,
        dataset_version=DATASET_VERSION,
        preprocessing_version=PREPROCESSING_VERSION,
        input_hash=input_hash,
        classification_hash=request.classification_hash,
        artifact_hash=artifact_hash(payload),
        bindings=_bindings(solver_id, solver_version),
        evidence=evidence,
        facts=[FactClaim(claim="solution was derived from raster pixels only", level=FactLevel.DERIVED, evidence_refs=["solver-input", "solver-decision"])],
        warnings=[warning] if warning else [],
    )


@dataclass(frozen=True)
class SliderSolver:
    solver_id: str = "reference-slider-solver"
    solver_version: str = "1.0.0"
    supported_families: frozenset[str] = frozenset({"slider"})

    def solve(self, request: SolveRequest) -> PredictionOutcome:
        raster = load_raster(request.assets[0])
        components = [
            component
            for component in mask_components(bright_mask(raster))
            if component.area >= 180 and 18 <= component.width <= 64 and 18 <= component.height <= 64 and component.fill_ratio >= 0.6
        ]
        components.sort(key=lambda item: (item.area * item.fill_ratio, -item.min_y, -item.min_x), reverse=True)
        if not components:
            return _outcome(request, solver_id=self.solver_id, solver_version=self.solver_version, raster=raster, status=PredictionStatus.LOW_CONFIDENCE, warning="no stable rectangular gap candidate")
        best = components[0]
        second = components[1].area * components[1].fill_ratio if len(components) > 1 else 0.0
        score = best.area * best.fill_ratio
        margin = (score - second) / max(score, 1.0)
        raw = min(1.0, 0.5 * best.fill_ratio + 0.5 * margin)
        confidence = _calibrate("slider", raw)
        if confidence < 0.65:
            return _outcome(request, solver_id=self.solver_id, solver_version=self.solver_version, raster=raster, status=PredictionStatus.LOW_CONFIDENCE, warning="slider candidate margin is below calibrated threshold")
        return _outcome(
            request,
            solver_id=self.solver_id,
            solver_version=self.solver_version,
            raster=raster,
            status=PredictionStatus.PRODUCED,
            solution=NormalizedSolution(type=SolutionType.OFFSET, offset=Offset(x=best.min_x, y=best.min_y)),
            confidence=confidence,
        )


@dataclass(frozen=True)
class RotateSolver:
    solver_id: str = "reference-rotate-solver"
    solver_version: str = "1.0.0"
    supported_families: frozenset[str] = frozenset({"rotate"})

    def solve(self, request: SolveRequest) -> PredictionOutcome:
        raster = load_raster(request.assets[0])
        components = [component for component in mask_components(red_mask(raster, 75)) if component.area >= 40]
        points = [point for component in components for point in component.pixels]
        if not points:
            return _outcome(request, solver_id=self.solver_id, solver_version=self.solver_version, raster=raster, status=PredictionStatus.LOW_CONFIDENCE, warning="no radial marker pixels")
        cx, cy = raster.width / 2, raster.height / 2
        bins = [0.0] * 360
        vector_x = 0.0
        vector_y = 0.0
        total = 0.0
        for x, y in points:
            dx, dy = x - cx, cy - y
            radius = math.hypot(dx, dy)
            if radius < min(raster.width, raster.height) * 0.12:
                continue
            angle = math.degrees(math.atan2(dy, dx)) % 360
            weight = radius
            bins[int(round(angle)) % 360] += weight
            vector_x += math.cos(math.radians(angle)) * weight
            vector_y += math.sin(math.radians(angle)) * weight
            total += weight
        if total <= 0:
            return _outcome(request, solver_id=self.solver_id, solver_version=self.solver_version, raster=raster, status=PredictionStatus.LOW_CONFIDENCE, warning="radial marker lacks an outer direction")
        smoothed = [sum(bins[(index + offset) % 360] for offset in range(-4, 5)) for index in range(360)]
        angle = max(range(360), key=lambda index: smoothed[index])
        concentration = math.hypot(vector_x, vector_y) / total
        peak = smoothed[angle]
        second = max(value for index, value in enumerate(smoothed) if abs((index - angle + 180) % 360 - 180) > 15)
        margin = max(0.0, (peak - second) / max(peak, 1.0))
        raw = min(1.0, 0.65 * concentration + 0.35 * margin)
        confidence = _calibrate("rotate", raw)
        if confidence < 0.65:
            return _outcome(request, solver_id=self.solver_id, solver_version=self.solver_version, raster=raster, status=PredictionStatus.LOW_CONFIDENCE, warning="rotate direction is ambiguous")
        return _outcome(
            request,
            solver_id=self.solver_id,
            solver_version=self.solver_version,
            raster=raster,
            status=PredictionStatus.PRODUCED,
            solution=NormalizedSolution(type=SolutionType.ANGLE, angle_degrees=float(angle)),
            confidence=confidence,
        )


@dataclass(frozen=True)
class ClickSolver:
    solver_id: str = "reference-click-solver"
    solver_version: str = "1.0.0"
    supported_families: frozenset[str] = frozenset({"click"})

    def solve(self, request: SolveRequest) -> PredictionOutcome:
        raster = load_raster(request.assets[0])
        groups = []
        for threshold in (70, 95):
            groups.append([
                component
                for component in mask_components(red_mask(raster, threshold))
                if 80 <= component.area <= 2500 and 0.55 <= component.fill_ratio <= 1.0 and 0.55 <= component.width / component.height <= 1.8
            ])
        if not groups[0] or len(groups[0]) != len(groups[1]):
            return _outcome(request, solver_id=self.solver_id, solver_version=self.solver_version, raster=raster, status=PredictionStatus.LOW_CONFIDENCE, warning="click components are unstable across thresholds")
        low = sorted((component.centroid for component in groups[0]), key=lambda point: (point[1], point[0]))
        high = sorted((component.centroid for component in groups[1]), key=lambda point: (point[1], point[0]))
        errors = [math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(low, high)]
        stability = 1.0 - min(1.0, sum(errors) / max(1.0, len(errors) * 6.0))
        confidence = _calibrate("click", 0.55 + 0.45 * stability)
        if confidence < 0.65:
            return _outcome(request, solver_id=self.solver_id, solver_version=self.solver_version, raster=raster, status=PredictionStatus.LOW_CONFIDENCE, warning="click centroid stability is below threshold")
        points = [Point(x=round((a[0] + b[0]) / 2, 3), y=round((a[1] + b[1]) / 2, 3)) for a, b in zip(low, high)]
        return _outcome(
            request,
            solver_id=self.solver_id,
            solver_version=self.solver_version,
            raster=raster,
            status=PredictionStatus.PRODUCED,
            solution=NormalizedSolution(type=SolutionType.POINTS, points=points),
            confidence=confidence,
        )


SOLVERS = {"slider": SliderSolver(), "rotate": RotateSolver(), "click": ClickSolver()}


def solve(request: SolveRequest) -> PredictionOutcome:
    try:
        family = ChallengeFamily(request.challenge_family).value
        if not request.authorization_record_id:
            return _outcome(request, solver_id="none", solver_version="0", raster=None, status=PredictionStatus.UNSUPPORTED, warning="solve requires local authorization")
        if request.classification_confidence is not None and request.classification_confidence < 0.65:
            return _outcome(request, solver_id="none", solver_version="0", raster=None, status=PredictionStatus.LOW_CONFIDENCE, warning="classification confidence is below dispatch threshold")
        solver = SOLVERS.get(family)
        if solver is None:
            return _outcome(request, solver_id="none", solver_version="0", raster=None, status=PredictionStatus.UNSUPPORTED, warning=f"unsupported challenge family: {family}")
        if request.solver_id and request.solver_id != solver.solver_id:
            return _outcome(request, solver_id=solver.solver_id, solver_version=solver.solver_version, raster=None, status=PredictionStatus.UNSUPPORTED, warning="requested solver does not match family registry dispatch")
        return solver.solve(request)
    except (OSError, RuntimeError, ValueError) as exc:
        return _outcome(request, solver_id="reference-dispatch", solver_version="1.0.0", raster=None, status=PredictionStatus.FAILED, warning=str(exc))
