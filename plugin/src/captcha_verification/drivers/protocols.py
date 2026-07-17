from __future__ import annotations

from typing import Protocol, runtime_checkable

from captcha_verification.contracts import ActionPlan, AuthorizationRecord, ExecutionReceipt


@runtime_checkable
class AuthorizedTestDriver(Protocol):
    driver_id: str

    def execute(self, *, plan: ActionPlan, authorization: AuthorizationRecord) -> ExecutionReceipt:
        """Execute a prevalidated plan and return an execution-only receipt."""
        ...


@runtime_checkable
class ObservationDriver(Protocol):
    driver_id: str

    def observe(self, *, target: str, authorization: AuthorizationRecord) -> dict[str, object]:
        """Collect an allowlisted observation without producing business acceptance."""
        ...
