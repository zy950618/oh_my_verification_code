from __future__ import annotations

from typing import Protocol

from captcha_verification.contracts import AuthorizationRecord


class AuthorizationRepository(Protocol):
    def resolve(self, authorization_id: str) -> AuthorizationRecord | None:
        """Return a trusted record, never a record supplied by the request."""
        ...


class InMemoryAuthorizationRepository:
    def __init__(self) -> None:
        self._records: dict[str, AuthorizationRecord] = {}

    def register(self, record: AuthorizationRecord) -> None:
        self._records[record.authorization_id] = record

    def resolve(self, authorization_id: str) -> AuthorizationRecord | None:
        return self._records.get(authorization_id)
