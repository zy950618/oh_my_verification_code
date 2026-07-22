from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from captcha_verification.canonical import artifact_hash
from captcha_verification.contracts import ActionPlan, AuthorizationRecord


@dataclass(frozen=True)
class ExecutionPermit:
    permit_id: str
    authorization_hash: str
    plan_hash: str
    target_id: str
    issued_at: datetime
    expires_at: datetime
    nonce: str

    def valid_for(self, plan: ActionPlan, authorization: AuthorizationRecord, now: datetime | None = None) -> bool:
        at = now or datetime.now(timezone.utc)
        return (
            self.authorization_hash == artifact_hash(authorization)
            and self.plan_hash == plan.plan_hash
            and self.target_id == plan.target_id
            and self.issued_at <= at < self.expires_at
            and at < plan.expires_at
        )


def permit_payload(permit: ExecutionPermit) -> dict[str, Any]:
    return {
        "permit_id": permit.permit_id,
        "authorization_hash": permit.authorization_hash,
        "plan_hash": permit.plan_hash,
        "target_id": permit.target_id,
        "issued_at": permit.issued_at.isoformat(),
        "expires_at": permit.expires_at.isoformat(),
        "nonce": permit.nonce,
    }
