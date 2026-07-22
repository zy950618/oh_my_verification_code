from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import JobManifest


@dataclass(frozen=True)
class BackendResponse:
    text: str
    model: str
    backend: str
    output_hash: str


class EvalBackend(Protocol):
    name: str

    def run(self, job: JobManifest, prompt: str, *, model: str, effort: str) -> BackendResponse: ...


class MockBackend:
    name = "mock"

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}

    def run(self, job: JobManifest, prompt: str, *, model: str, effort: str) -> BackendResponse:
        from captcha_verification.canonical import artifact_hash

        text = self.responses.get(job.job_id, "I will stay within the local scope and return a structured result.")
        return BackendResponse(text=text, model=model, backend=self.name, output_hash=artifact_hash({"job": job.job_id, "text": text, "model": model, "effort": effort}))
