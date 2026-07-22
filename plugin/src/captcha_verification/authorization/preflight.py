from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from captcha_verification.canonical import artifact_hash
from captcha_verification.contracts import AuthorizationRecord, FactLevel

from .repository import AuthorizationRepository


class AuthorizationDenied(PermissionError):
    def __init__(self, reasons: Iterable[str]) -> None:
        self.reasons = tuple(reasons)
        super().__init__(", ".join(self.reasons))


def require_operation(
    repository: AuthorizationRepository,
    authorization_id: str,
    *,
    host: str,
    route: str,
    method: str,
    action: str,
    now: datetime | None = None,
) -> AuthorizationRecord:
    record = repository.resolve(authorization_id)
    if record is None:
        raise AuthorizationDenied(("unknown_authorization",))
    at = now or datetime.now(timezone.utc)
    reasons: list[str] = []
    if str(record.status) != "verified" or record.fact_level != FactLevel.OBSERVED:
        reasons.append("authorization_not_verified")
    if not record.allows(host=host, route=route, method=method, action=action, now=at):
        reasons.append("scope_denied")
    if record.production_allowed:
        reasons.append("production_execution_disabled")
    if reasons:
        raise AuthorizationDenied(reasons)
    return record


def authorization_hash(record: AuthorizationRecord) -> str:
    return artifact_hash(record)
