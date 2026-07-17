from __future__ import annotations

from typing import Protocol

from captcha_verification.contracts import PredictionOutcome, SolveRequest


class Solver(Protocol):
    solver_id: str
    solver_version: str
    supported_families: frozenset[str]

    def solve(self, request: SolveRequest) -> PredictionOutcome: ...
