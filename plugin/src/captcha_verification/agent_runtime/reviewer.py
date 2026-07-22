from __future__ import annotations

from captcha_verification.canonical import artifact_hash

from .contracts import ResultManifest, ReviewVerdict
from .policy import scan_file_for_secrets


class IndependentReviewer:
    name = "independent-rule-reviewer-v1"

    def review(self, result: ResultManifest) -> ReviewVerdict:
        findings: list[str] = []
        missing = list(result.missing_evidence)
        secret = False
        for artifact in result.artifacts:
            path = __import__("pathlib").Path(artifact.path)
            if path.exists() and scan_file_for_secrets(path):
                secret = True
                findings.append(f"secret-like artifact: {artifact.path}")
        overclaim = result.business_success == "accepted" and result.evidence_stage not in {"E5_authorized_business_accepted", "E6_repeat_verified"}
        if overclaim:
            findings.append("business success lacks first-party acceptance and repeat evidence")
            missing.extend(["first_party_business_receipt", "repeat_acceptance", "negative_control_ledger_delta"])
        scope_violation = result.external_network_used and result.evidence_stage not in {"E5_authorized_business_accepted", "E6_repeat_verified"}
        if scope_violation:
            findings.append("external network use is outside local evidence scope")
        if result.status == "blocked":
            verdict = "unverified"
        elif secret or overclaim or scope_violation:
            verdict = "rejected"
        elif result.status != "completed" or missing:
            verdict = "needs_human_review"
        else:
            verdict = "accepted"
        return ReviewVerdict(
            job_id=result.job_id,
            verdict=verdict,
            findings=findings,
            evidence_paths=[artifact.path for artifact in result.artifacts],
            missing_evidence=sorted(set(missing)),
            reviewer=self.name,
            reviewer_hash=artifact_hash({"reviewer": self.name, "rules": ["scope", "secret", "evidence", "network"]}),
            overclaim_detected=overclaim,
            secret_leak_detected=secret,
            scope_violation_detected=scope_violation,
            positive_claim_allowed=verdict == "accepted" and result.evidence_stage in {"E5_authorized_business_accepted", "E6_repeat_verified"},
        )
