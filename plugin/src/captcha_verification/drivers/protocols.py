from __future__ import annotations

from typing import Protocol

from captcha_verification.contracts import ActionPlan, AuthorizationRecord, ExecutionReceipt
from captcha_verification.runtime import ExecutionPermit


@runtime_checkable
class AuthorizedTestDriver(Protocol):
    driver_id: str

    def execute(self, *, plan: ActionPlan, authorization: AuthorizationRecord, permit: ExecutionPermit) -> ExecutionReceipt:
        """Execute a prevalidated plan only while its permit is valid."""
        ...


@runtime_checkable
class ObservationDriver(Protocol):
    driver_id: str

    def observe(self, *, target: str, authorization: AuthorizationRecord) -> dict[str, object]:
        """Collect an allowlisted observation without producing business acceptance."""
        ...
