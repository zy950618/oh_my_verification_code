from __future__ import annotations

import uuid

from captcha_verification.canonical import artifact_hash
from captcha_verification.contracts import (
    ArtifactBinding,
    ChallengeFamily,
    ClassificationRequest,
    ClassificationResult,
    EvidenceRef,
    FactClaim,
    FactLevel,
    PredictionStatus,
    ProviderCandidate,
)
from captcha_verification.raster import bright_mask, load_raster, mask_components, red_mask


CLASSIFIER_ID = "reference-raster-classifier"
CLASSIFIER_VERSION = "1.0.0"
CLASSIFIER_CONFIG = {
    "families": ["slider", "rotate", "click"],
    "minimum_dimensions": [16, 16],
    "red_excess_thresholds": [70, 95],
    "bright_sum_threshold": 705,
}
CLASSIFIER_HASH = artifact_hash(CLASSIFIER_CONFIG)


def _evidence(evidence_id: str, uri: str, sha256: str | None, level: FactLevel) -> EvidenceRef:
    return EvidenceRef(evidence_id=evidence_id, uri=uri, sha256=sha256, fact_level=level)


def classify(request: ClassificationRequest) -> ClassificationResult:
    classification_id = f"classification-{uuid.uuid5(uuid.NAMESPACE_URL, request.request_id)}"
    if not request.authorization_record_id:
        return ClassificationResult(
            classification_id=classification_id,
            provider_candidates=[ProviderCandidate(provider="unknown", confidence=0.0)],
            challenge_family=ChallengeFamily.UNKNOWN,
            confidence=0.0,
            required_solver_capability="none",
            authorization_decision="missing_verified_authorization",
            classifier_version=CLASSIFIER_VERSION,
            classifier_hash=CLASSIFIER_HASH,
            input_hash=artifact_hash([asset.sha256 for asset in request.assets]),
            status=PredictionStatus.UNSUPPORTED,
            warnings=["classification requires a local authorization record reference"],
        )
    if len(request.assets) != 1:
        raise ValueError("reference classifier requires exactly one raster asset")
    try:
        raster = load_raster(request.assets[0])
    except (RuntimeError, ValueError) as exc:
        return ClassificationResult(
            classification_id=classification_id,
            provider_candidates=[ProviderCandidate(provider="unknown", confidence=0.0)],
            challenge_family=ChallengeFamily.UNKNOWN,
            confidence=0.0,
            required_solver_capability="none",
            authorization_decision="local_fixture_only",
            classifier_version=CLASSIFIER_VERSION,
            classifier_hash=CLASSIFIER_HASH,
            input_hash=artifact_hash([asset.sha256 for asset in request.assets]),
            status=PredictionStatus.UNSUPPORTED,
            warnings=[str(exc)],
        )

    red_lo = [component for component in mask_components(red_mask(raster, 70)) if component.area >= 40]
    red_hi = [component for component in mask_components(red_mask(raster, 95)) if component.area >= 40]
    bright = [
        component
        for component in mask_components(bright_mask(raster))
        if component.area >= 180 and 18 <= component.width <= 64 and 18 <= component.height <= 64
    ]
    aspect = raster.width / raster.height
    family = ChallengeFamily.UNKNOWN
    confidence = 0.0
    markers: list[str] = [f"aspect_ratio={aspect:.4f}", f"red_components={len(red_hi)}", f"bright_gap_candidates={len(bright)}"]
    if aspect >= 1.45 and bright:
        family = ChallengeFamily.SLIDER
        best = max(bright, key=lambda item: item.area)
        confidence = min(0.97, 0.68 + 0.2 * best.fill_ratio + min(0.09, best.area / 5000))
        markers.append(f"rectangular_gap_fill={best.fill_ratio:.4f}")
    elif 0.82 <= aspect <= 1.22 and red_hi:
        family = ChallengeFamily.ROTATE
        confidence = min(0.96, 0.72 + min(0.2, sum(component.area for component in red_hi) / 5000))
        markers.append("near_square_radial_candidate")
    elif 1.2 <= aspect < 1.8 and red_hi and abs(len(red_lo) - len(red_hi)) <= 1:
        family = ChallengeFamily.CLICK
        stability = 1.0 - abs(len(red_lo) - len(red_hi)) / max(1, len(red_lo))
        confidence = min(0.95, 0.67 + 0.2 * stability + min(0.08, len(red_hi) * 0.02))
        markers.append(f"component_threshold_stability={stability:.4f}")

    status = PredictionStatus.PRODUCED if family != ChallengeFamily.UNKNOWN and confidence >= 0.65 else PredictionStatus.LOW_CONFIDENCE
    if status != PredictionStatus.PRODUCED:
        family = ChallengeFamily.UNKNOWN
    observed = _evidence("raster", request.assets[0].uri, raster.sha256, FactLevel.OBSERVED)
    derived = _evidence("classifier-features", "memory://reference-classifier/features", artifact_hash(markers), FactLevel.DERIVED)
    target_observed = request.context.get("target_id") == "local-reference-runtime"
    provider = "first_party_local_reference" if target_observed else "unknown"
    provider_confidence = 1.0 if target_observed else 0.0
    binding = ArtifactBinding(registry_kind="classifier", entry_id=CLASSIFIER_ID, version=CLASSIFIER_VERSION, artifact_hash=CLASSIFIER_HASH)
    return ClassificationResult(
        classification_id=classification_id,
        provider_candidates=[ProviderCandidate(provider=provider, confidence=provider_confidence, markers=markers, evidence=[observed, derived])],
        challenge_family=family,
        confidence=confidence,
        required_solver_capability=f"reference-{family.value}-solver" if family != ChallengeFamily.UNKNOWN else "none",
        authorization_decision="authorized_local_fixture",
        classifier_version=CLASSIFIER_VERSION,
        classifier_hash=CLASSIFIER_HASH,
        classifier_binding=binding,
        input_hash=raster.sha256,
        status=status,
        evidence=[observed, derived],
        facts=[
            FactClaim(claim="raster dimensions and hash were decoded locally", level=FactLevel.OBSERVED, evidence_refs=["raster"]),
            FactClaim(claim=f"challenge family derived as {family.value}", level=FactLevel.DERIVED, evidence_refs=["classifier-features"]),
        ],
        warnings=[] if status == PredictionStatus.PRODUCED else ["fixture does not meet a calibrated reference family boundary"],
    )
