from __future__ import annotations

from dataclasses import dataclass

from captcha_verification.contracts import NormalizedSolution, PredictionOutcome, PredictionStatus, Press, SolutionType, SolveRequest
from captcha_verification.raster import load_raster


@dataclass(frozen=True)
class PressSolver:
    solver_id: str = "reference-press-solver"
    solver_version: str = "1.0.0"
    supported_families: frozenset[str] = frozenset({"press"})
    supported_solution_types: frozenset[SolutionType] = frozenset({SolutionType.PRESS})

    def solve(self, request: SolveRequest) -> PredictionOutcome:
        from .reference import _outcome

        raster = load_raster(request.assets[0])
        return _outcome(
            request,
            solver_id=self.solver_id,
            solver_version=self.solver_version,
            raster=raster,
            status=PredictionStatus.LOW_CONFIDENCE,
            warning="reference press detector requires a calibrated visible duration signal",
        )
