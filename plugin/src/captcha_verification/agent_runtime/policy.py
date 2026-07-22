from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid5, NAMESPACE_URL

from captcha_verification.canonical import artifact_hash, file_sha256

from .contracts import (
    AgentPolicyManifest,
    JobManifest,
    PolicyReceipt,
    RuntimePolicyDecision,
    Scope,
)

_DANGEROUS = (
    "jailbreak", "unrestricted", "ignore authorization", "bypass", "stealth",
    "fingerprint spoof", "clearance cookie", "browser profile", "credential",
    "access token", "api token", "password", "raw har", "business success claim",
)
_SECRET = re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|secret|password|cookie|authorization)\s*[:=]\s*[^\s]+")


def restricted_terms(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({term for term in _DANGEROUS if term in lowered})


def redact_text(text: str) -> str:
    return _SECRET.sub(lambda match: match.group(0).split("=", 1)[0].split(":", 1)[0] + "=<redacted>", text)


def is_loopback_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and parsed.hostname in {"localhost", "127.0.0.1", "::1"}


def _allowed_host(host: str, scope: Scope) -> bool:
    return host.lower().rstrip(".") in {item.lower().rstrip(".") for item in scope.allowed_hosts}


def evaluate_policy(job: JobManifest, policy: AgentPolicyManifest) -> RuntimePolicyDecision:
    denied: list[str] = []
    if job.mode not in policy.allowed_modes:
        denied.append("mode_not_allowed_by_policy")
    if job.scope.authorization_status in {"claimed_unverified", "expired", "revoked"} and job.mode == "owned_authorized":
        denied.append("authorization_not_verified")
    if job.scope.target_environment == "owned_authorized" and not job.scope.authorization_evidence:
        denied.append("authorization_evidence_missing")
    text = " ".join([job.objective, *job.forbidden_operations, *job.allowed_tools])
    denied.extend(f"restricted_operation:{term}" for term in restricted_terms(text))
    if policy.sandbox_profile.credentials:
        denied.append("credential_access_forbidden")
    if job.sandbox_profile.credentials:
        denied.append("credential_access_forbidden")
    if job.sandbox_profile.network == "allowlisted" and not job.sandbox_profile.allowed_hosts:
        denied.append("network_allowlist_missing")
    if job.mode == "offline_compute" and job.sandbox_profile.network != "none":
        denied.append("offline_compute_must_be_networkless")
    allowed = not denied
    return RuntimePolicyDecision(
        allowed=allowed,
        job_id=job.job_id,
        scope=job.mode,
        reason="policy_allow" if allowed else "policy_blocked",
        denied_reasons=denied,
        network_allowed=job.sandbox_profile.network != "none",
        external_generalization_allowed=False,
    )


def policy_receipt(job: JobManifest, policy: AgentPolicyManifest, decision: RuntimePolicyDecision) -> PolicyReceipt:
    job_hash = artifact_hash(job.model_dump(mode="json"))
    policy_hash = artifact_hash(policy.model_dump(mode="json"))
    receipt_id = f"policy-{uuid5(NAMESPACE_URL, job_hash + policy_hash)}"
    return PolicyReceipt(receipt_id=receipt_id, job_id=job.job_id, policy_hash=policy_hash, job_hash=job_hash, decision=decision)


def safe_path(path: Path, roots: tuple[Path, ...], *, must_exist: bool = False) -> Path:
    resolved = path.resolve(strict=must_exist)
    approved = [root.resolve(strict=False) for root in roots]
    if not any(resolved == root or root in resolved.parents for root in approved):
        raise PermissionError("path is outside approved roots")
    return resolved


def scan_file_for_secrets(path: Path, *, max_bytes: int = 2_000_000) -> list[str]:
    if path.stat().st_size > max_bytes:
        return ["artifact_too_large_to_scan"]
    text = path.read_text(encoding="utf-8", errors="replace")
    return ["secret_like_content"] if _SECRET.search(text) else []


def artifact_digest(path: Path) -> str:
    return file_sha256(path)
