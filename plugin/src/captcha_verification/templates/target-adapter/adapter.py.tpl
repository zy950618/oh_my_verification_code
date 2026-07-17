from __future__ import annotations

from captcha_verification.contracts import ActionPlan, AuthorizationRecord, ExecutionReceipt


class {{ class_name }}Adapter:
    """Generated provider-neutral adapter stub.

    Generation does not validate compatibility and does not execute the target.
    """

    adapter_id = "{{ adapter_id }}"

    def classify(self, request: object) -> object:
        raise NotImplementedError("classify is missing evidence and implementation")

    def solve(self, request: object) -> object:
        raise NotImplementedError("solve is missing evidence and implementation")

    def plan_action(self, request: object) -> ActionPlan:
        raise NotImplementedError("plan_action is missing evidence and implementation")

    def execute(self, *, plan: ActionPlan, authorization: AuthorizationRecord) -> ExecutionReceipt:
        raise NotImplementedError("execution requires a separately validated authorization scope")
