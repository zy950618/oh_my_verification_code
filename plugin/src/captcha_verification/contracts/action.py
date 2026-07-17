from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from captcha_verification.canonical import artifact_hash

from .artifacts import ArtifactBinding
from .common import ContractModel, EvidenceRef, FactClaim
from .enums import ActionKind, BusinessAcceptanceStatus, CaptureSpace, ExecutionStatus, ProviderVerificationStatus, ReceiptKind


class FrameTransform(ContractModel):
    frame_id: str
    offset_x: float = 0
    offset_y: float = 0
    scroll_x: float = 0
    scroll_y: float = 0
    border_x: float = 0
    border_y: float = 0


class CoordinateFrame(ContractModel):
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    device_pixel_ratio: float = Field(gt=0)
    capture_space: CaptureSpace = CaptureSpace.INTRINSIC_IMAGE_PX
    intrinsic_width: float | None = Field(default=None, gt=0)
    intrinsic_height: float | None = Field(default=None, gt=0)
    crop_x: float = 0
    crop_y: float = 0
    rendered_x: float = 0
    rendered_y: float = 0
    rendered_width: float | None = Field(default=None, gt=0)
    rendered_height: float | None = Field(default=None, gt=0)
    scroll_x: float = 0
    scroll_y: float = 0
    iframe_x: float = 0
    iframe_y: float = 0
    frame_chain: list[FrameTransform] = Field(default_factory=list)
    rounding: Literal["nearest", "floor", "ceil"] = "nearest"


class TransformRecord(ContractModel):
    step: str
    input_x: float
    input_y: float
    output_x: float
    output_y: float
    details: dict[str, float | str] = Field(default_factory=dict)


class Action(ContractModel):
    kind: ActionKind
    time_ms: int = Field(ge=0)
    x: float | None = None
    y: float | None = None
    text: str | None = None
    duration_ms: int | None = Field(default=None, gt=0)
    angle_degrees: float | None = None


class PlanActionRequest(ContractModel):
    schema_version: str = "captcha-plan-action-request/v1"
    request_id: str
    prediction: dict[str, object]
    challenge_instance_id: str
    authorization_record_id: str
    session_binding_hash: str
    target_id: str
    coordinate_frame: CoordinateFrame
    created_at: datetime
    expires_at: datetime
    minimum_confidence: float = Field(default=0.65, ge=0, le=1)


class ActionPlan(ContractModel):
    schema_version: str = "captcha-action-plan/v1"
    plan_id: str
    challenge_instance_id: str
    source_prediction_id: str
    source_prediction_hash: str | None = None
    input_hash: str | None = None
    session_binding_hash: str | None = None
    target_id: str | None = None
    planner_binding: ArtifactBinding | None = None
    coordinate_frame: CoordinateFrame
    transforms: list[TransformRecord] = Field(default_factory=list)
    actions: list[Action]
    constraints: list[str] = Field(default_factory=list)
    stop_conditions: list[str]
    maximum_action_count: int = Field(default=16, gt=0)
    created_at: datetime
    expires_at: datetime
    authorization_record_id: str
    plan_hash: str | None = None
    executable: Literal[False] = False

    @model_validator(mode="after")
    def validate_actions(self) -> "ActionPlan":
        if not self.actions:
            raise ValueError("actions must not be empty")
        if len(self.actions) > self.maximum_action_count:
            raise ValueError("actions exceed maximum_action_count")
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
        expected = artifact_hash(self)
        if self.plan_hash is None:
            self.plan_hash = expected
        elif self.plan_hash != expected:
            raise ValueError("plan_hash does not match plan content")
        return self


class ActualAction(Action):
    observed_at: datetime


class ExecutionReceipt(ContractModel):
    schema_version: str = "captcha-execution-receipt/v1"
    kind: Literal[ReceiptKind.LOCAL_EXECUTION] = ReceiptKind.LOCAL_EXECUTION
    audience: Literal["local_provider_verifier"] = "local_provider_verifier"
    receipt_id: str
    receipt_hash: str | None = None
    plan_id: str
    plan_hash: str | None = None
    input_hash: str | None = None
    challenge_instance_id: str
    session_binding_hash: str | None = None
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
        expected = artifact_hash(self)
        if self.receipt_hash is None:
            self.receipt_hash = expected
        elif self.receipt_hash != expected:
            raise ValueError("execution receipt hash does not match content")
        return self


class ProviderVerificationReceipt(ContractModel):
    schema_version: str = "captcha-provider-verification-receipt/v1"
    kind: Literal[ReceiptKind.PROVIDER] = ReceiptKind.PROVIDER
    audience: Literal["first_party_business_api"] = "first_party_business_api"
    receipt_id: str
    receipt_hash: str | None = None
    parent_execution_receipt_hash: str | None = None
    plan_hash: str | None = None
    session_binding_hash: str | None = None
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
    expires_at: datetime | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_boundaries(self) -> "ProviderVerificationReceipt":
        if self.test_key_used and self.status == ProviderVerificationStatus.ACCEPTED:
            self.status = ProviderVerificationStatus.BOUNDARY_ONLY
        if self.status == ProviderVerificationStatus.ACCEPTED:
            if not self.response_assertions_passed:
                raise ValueError("accepted provider receipts require response assertions")
            if self.expected_action and self.expected_action != self.observed_action:
                raise ValueError("provider action does not match")
            if self.expected_hostname and self.expected_hostname != self.observed_hostname:
                raise ValueError("provider hostname does not match")
        expected = artifact_hash(self)
        if self.receipt_hash is None:
            self.receipt_hash = expected
        elif self.receipt_hash != expected:
            raise ValueError("provider receipt hash does not match content")
        return self
