from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .common import ContractModel, EvidenceRef, FactClaim
from .enums import ActionKind, BusinessAcceptanceStatus, ExecutionStatus, ProviderVerificationStatus


class CoordinateFrame(ContractModel):
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    device_pixel_ratio: float = Field(gt=0)
    crop_x: float = 0
    crop_y: float = 0
    scroll_x: float = 0
    scroll_y: float = 0
    iframe_x: float = 0
    iframe_y: float = 0
    rounding: str = "nearest"


class Action(ContractModel):
    kind: ActionKind
    time_ms: int = Field(ge=0)
    x: float | None = None
    y: float | None = None
    text: str | None = None
    duration_ms: int | None = Field(default=None, gt=0)
    angle_degrees: float | None = None


class ActionPlan(ContractModel):
    schema_version: str = "captcha-action-plan/v1"
    plan_id: str
    challenge_instance_id: str
    source_prediction_id: str
    coordinate_frame: CoordinateFrame
    actions: list[Action]
    constraints: list[str] = Field(default_factory=list)
    stop_conditions: list[str]
    created_at: datetime
    expires_at: datetime
    authorization_record_id: str
    executable: Literal[False] = False

    @model_validator(mode="after")
    def validate_actions(self) -> "ActionPlan":
        if not self.actions:
            raise ValueError("actions must not be empty")
        if not self.stop_conditions:
            raise ValueError("stop_conditions must not be empty")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        previous = -1
        frame = self.coordinate_frame
        coordinate_kinds = {
            ActionKind.POINTER_DOWN,
            ActionKind.POINTER_MOVE,
            ActionKind.POINTER_UP,
            ActionKind.TAP,
            ActionKind.CLICK,
            ActionKind.PRESS,
        }
        for index, action in enumerate(self.actions):
            if action.time_ms < previous:
                raise ValueError(f"actions[{index}].time_ms must be monotonic")
            previous = action.time_ms
            if action.kind in coordinate_kinds:
                if action.x is None or action.y is None:
                    raise ValueError(f"actions[{index}] requires x and y")
                if not (0 <= action.x <= frame.width and 0 <= action.y <= frame.height):
                    raise ValueError(f"actions[{index}] is outside the coordinate frame")
            if action.kind == ActionKind.TYPE_TEXT and not action.text:
                raise ValueError(f"actions[{index}] requires text")
            if action.kind == ActionKind.PRESS and action.duration_ms is None:
                raise ValueError(f"actions[{index}] requires duration_ms")
            if action.kind == ActionKind.ROTATE and action.angle_degrees is None:
                raise ValueError(f"actions[{index}] requires angle_degrees")
        return self


class ActualAction(Action):
    observed_at: datetime


class ExecutionReceipt(ContractModel):
    schema_version: str = "captcha-execution-receipt/v1"
    receipt_id: str
    plan_id: str
    challenge_instance_id: str
    driver_id: str
    status: ExecutionStatus
    started_at: datetime
    ended_at: datetime
    actual_actions: list[ActualAction] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    facts: list[FactClaim] = Field(default_factory=list)
    provider_verification_status: ProviderVerificationStatus = ProviderVerificationStatus.NOT_ATTEMPTED
    business_acceptance_status: Literal[BusinessAcceptanceStatus.NOT_ATTEMPTED] = BusinessAcceptanceStatus.NOT_ATTEMPTED

    @model_validator(mode="after")
    def validate_times(self) -> "ExecutionReceipt":
        if self.ended_at < self.started_at:
            raise ValueError("ended_at must not precede started_at")
        return self


class ProviderVerificationReceipt(ContractModel):
    schema_version: str = "captcha-provider-verification-receipt/v1"
    receipt_id: str
    challenge_instance_id: str
    status: ProviderVerificationStatus
    provider: str
    transport_status: int | None = None
    response_assertions_passed: bool = False
    expected_action: str | None = None
    observed_action: str | None = None
    expected_hostname: str | None = None
    observed_hostname: str | None = None
    test_key_used: bool = False
    verified_at: datetime
    evidence: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_test_key_boundary(self) -> "ProviderVerificationReceipt":
        if self.test_key_used and self.status == ProviderVerificationStatus.ACCEPTED:
            self.status = ProviderVerificationStatus.BOUNDARY_ONLY
        if self.status == ProviderVerificationStatus.ACCEPTED:
            if not self.response_assertions_passed:
                raise ValueError("accepted provider receipts require response assertions")
            if self.expected_action and self.expected_action != self.observed_action:
                raise ValueError("provider action does not match")
            if self.expected_hostname and self.expected_hostname != self.observed_hostname:
                raise ValueError("provider hostname does not match")
        return self
