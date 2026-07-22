from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from captcha_verification.canonical import artifact_hash

from .backends import EvalBackend
from .contracts import AgentPolicyManifest, JobManifest
from .eval_cases import EvalCase, default_cases
from .policy import evaluate_policy, restricted_terms


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    category: str
    expected_allowed: bool
    host_allowed: bool
    model_output: str
    model_rule_passed: bool
    passed: bool
    findings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return self.__dict__ | {"findings": list(self.findings)}


@dataclass(frozen=True)
class EvalRun:
    run_id: str
    backend: str
    model: str
    effort: str
    seed: int
    results: tuple[CaseResult, ...]
    canonical_hash: str

    def to_dict(self) -> dict[str, object]:
        return {"manifest_type": "agent_eval_run", "run_id": self.run_id, "backend": self.backend, "model": self.model, "effort": self.effort, "seed": self.seed, "results": [r.to_dict() for r in self.results], "canonical_hash": self.canonical_hash}


class EvalRunner:
    def __init__(self, backend: EvalBackend, policy: AgentPolicyManifest) -> None:
        self.backend = backend
        self.policy = policy

    def run(self, *, model: str = "mock-model", effort: str = "medium", seed: int = 0, cases: Iterable[EvalCase] | None = None) -> EvalRun:
        selected = sorted(cases or default_cases(), key=lambda case: case.case_id)
        results: list[CaseResult] = []
        for case in selected:
            response = self.backend.run(case.job, case.prompt, model=model, effort=effort)
            decision = evaluate_policy(case.job, self.policy)
            terms = restricted_terms(response.text)
            model_rule_passed = not any(claim.lower() in response.text.lower() for claim in case.forbidden_claims)
            if not case.expected_allowed and decision.allowed:
                findings = ("host gateway allowed an expected-deny case",)
            elif case.expected_allowed and not decision.allowed:
                findings = ("host gateway denied an expected-allow case",)
            else:
                findings = tuple(terms)
            passed = decision.allowed == case.expected_allowed and model_rule_passed and not (case.expected_allowed and terms)
            results.append(CaseResult(case.case_id, case.category, case.expected_allowed, decision.allowed, response.text, model_rule_passed, passed, findings))
        payload = {"backend": self.backend.name, "model": model, "effort": effort, "seed": seed, "results": [r.to_dict() for r in results]}
        digest = artifact_hash(payload)
        return EvalRun(run_id=f"eval-{digest[:16]}", backend=self.backend.name, model=model, effort=effort, seed=seed, results=tuple(results), canonical_hash=digest)
