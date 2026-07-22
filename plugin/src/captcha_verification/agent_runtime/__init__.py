"""Provider-neutral AI job orchestration for local and authorized workflows."""

from .backends import BackendResponse, EvalBackend, MockBackend
from .codex_adapter import CodexAdapter
from .contracts import (
    AcceptanceCriteria,
    AgentPolicyManifest,
    ArtifactRecord,
    AttemptRecord,
    BinaryExecutionReceipt,
    JobManifest,
    PolicyReceipt,
    PromptPackManifest,
    ResourceLimits,
    ResultManifest,
    ReviewVerdict,
    RuntimePolicyDecision,
    SandboxProfile,
    Scope,
)
from .eval_runner import EvalRun, EvalRunner
from .provenance import ProvenanceRecord, ProvenanceRegistry
from .reviewer import IndependentReviewer
from .policy import evaluate_policy, policy_receipt

try:
    from .prompt_packs import PromptInstallPlan, PromptPackInstaller
except ImportError:  # pragma: no cover
    PromptInstallPlan = None
    PromptPackInstaller = None

try:
    from captcha_verification.canonical import artifact_hash as canonical_hash
except ImportError:  # pragma: no cover
    canonical_hash = None

__all__ = [
    "AcceptanceCriteria", "AgentPolicyManifest", "ArtifactRecord", "AttemptRecord", "BinaryExecutionReceipt", "BackendResponse", "CodexAdapter",
    "EvalBackend", "EvalRun", "EvalRunner", "IndependentReviewer", "JobManifest", "MockBackend", "PolicyReceipt",
    "PromptPackManifest", "PromptInstallPlan", "PromptPackInstaller", "ProvenanceRecord", "ProvenanceRegistry",
    "ResourceLimits", "ResultManifest", "ReviewVerdict", "RuntimePolicyDecision", "SandboxProfile", "Scope",
    "canonical_hash", "evaluate_policy", "policy_receipt",
]
