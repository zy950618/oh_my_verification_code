from __future__ import annotations

from dataclasses import dataclass

from captcha_verification.contracts import NormalizedSolution, PredictionOutcome, PredictionStatus, SolutionType, SolveRequest
from captcha_verification.raster import load_raster


@dataclass(frozen=True)
class TextSolver:
    solver_id: str = "reference-text-solver"
    solver_version: str = "1.0.0"
    supported_families: frozenset[str] = frozenset({"text"})
    supported_solution_types: frozenset[SolutionType] = frozenset({SolutionType.TEXT})

    def solve(self, request: SolveRequest) -> PredictionOutcome:
        from .reference import _outcome

        raster = load_raster(request.assets[0])
        # The reference runtime has no OCR weights. It abstains on unknown glyphs
        # instead of reading filenames, labels, DOM metadata, or server answers.
        return _outcome(
            request,
            solver_id=self.solver_id,
            solver_version=self.solver_version,
            raster=raster,
            status=PredictionStatus.LOW_CONFIDENCE,
            warning="reference text OCR implementation is not calibrated for this raster",
        )
