from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from captcha_verification.canonical import artifact_hash
from captcha_verification.contracts import (
    Action,
    ActionKind,
    ActionPlan,
    ArtifactBinding,
    CaptureSpace,
    CoordinateFrame,
    NormalizedSolution,
    PlanActionRequest,
    PredictionOutcome,
    PredictionStatus,
    SolutionType,
    TransformRecord,
)


PLANNER_ID = "reference-action-planner"
PLANNER_VERSION = "1.0.0"
PLANNER_HASH = artifact_hash({"id": PLANNER_ID, "version": PLANNER_VERSION, "executable": False})
STOP_CONDITIONS = [
    "challenge_instance_changed",
    "plan_expired",
    "provider_rejected",
    "business_state_reached",
    "no_retry_without_fresh_challenge",
]


def _round(value: float, policy: str) -> float:
    if policy == "floor":
        return float(math.floor(value))
    if policy == "ceil":
        return float(math.ceil(value))
    return float(round(value))


def map_point(x: float, y: float, frame: CoordinateFrame) -> tuple[float, float, list[TransformRecord]]:
    records: list[TransformRecord] = []

    def record(step: str, before: tuple[float, float], after: tuple[float, float], **details: float | str) -> tuple[float, float]:
        records.append(
            TransformRecord(
                step=step,
                input_x=before[0],
                input_y=before[1],
                output_x=after[0],
                output_y=after[1],
                details=details,
            )
        )
        return after

    point = record("uncrop", (x, y), (x + frame.crop_x, y + frame.crop_y), crop_x=frame.crop_x, crop_y=frame.crop_y)
    if frame.capture_space == CaptureSpace.SCREENSHOT_DEVICE_PX:
        point = record(
            "device_px_to_css_px",
            point,
            (point[0] / frame.device_pixel_ratio, point[1] / frame.device_pixel_ratio),
            device_pixel_ratio=frame.device_pixel_ratio,
        )
    intrinsic_width = frame.intrinsic_width or frame.width
    intrinsic_height = frame.intrinsic_height or frame.height
    rendered_width = frame.rendered_width or intrinsic_width
    rendered_height = frame.rendered_height or intrinsic_height
    scaled = (point[0] * rendered_width / intrinsic_width, point[1] * rendered_height / intrinsic_height)
    point = record("intrinsic_to_rendered", point, scaled, scale_x=rendered_width / intrinsic_width, scale_y=rendered_height / intrinsic_height)
    point = record("element_to_inner_document", point, (point[0] + frame.rendered_x, point[1] + frame.rendered_y), rendered_x=frame.rendered_x, rendered_y=frame.rendered_y)
    point = record("inner_document_to_viewport", point, (point[0] - frame.scroll_x, point[1] - frame.scroll_y), scroll_x=frame.scroll_x, scroll_y=frame.scroll_y)
    if frame.iframe_x or frame.iframe_y:
        point = record("legacy_iframe_origin", point, (point[0] + frame.iframe_x, point[1] + frame.iframe_y), iframe_x=frame.iframe_x, iframe_y=frame.iframe_y)
    for current in frame.frame_chain:
        point = record(
            f"iframe:{current.frame_id}",
            point,
            (
                point[0] - current.scroll_x + current.offset_x + current.border_x,
                point[1] - current.scroll_y + current.offset_y + current.border_y,
            ),
            scroll_x=current.scroll_x,
            scroll_y=current.scroll_y,
            offset_x=current.offset_x,
            offset_y=current.offset_y,
            border_x=current.border_x,
            border_y=current.border_y,
        )
    rounded = (_round(point[0], frame.rounding), _round(point[1], frame.rounding))
    point = record("round_final", point, rounded, policy=frame.rounding)
    return point[0], point[1], records


def plan_action(request: PlanActionRequest) -> ActionPlan:
    prediction = PredictionOutcome.model_validate(request.prediction)
    now = datetime.now(timezone.utc)
    if PredictionStatus(prediction.status) != PredictionStatus.PRODUCED:
        raise ValueError("planner requires a produced prediction")
    if prediction.confidence is None or prediction.confidence < request.minimum_confidence:
        raise ValueError("prediction confidence is below planner threshold")
    if prediction.challenge_instance_id != request.challenge_instance_id:
        raise ValueError("prediction challenge instance does not match request")
    if not prediction.input_hash or not prediction.classification_hash or not prediction.artifact_hash:
        raise ValueError("planner requires prediction input, classification, and artifact hashes")
    if request.expires_at <= request.created_at or request.expires_at <= now:
        raise ValueError("plan expiry must be in the future")
    solution = NormalizedSolution.model_validate(prediction.solution)
    actions: list[Action] = []
    transforms: list[TransformRecord] = []
    solution_type = SolutionType(solution.type)
    if solution_type == SolutionType.OFFSET and solution.offset:
        start_x, start_y, first = map_point(0, solution.offset.y, request.coordinate_frame)
        end_x, end_y, second = map_point(solution.offset.x, solution.offset.y, request.coordinate_frame)
        transforms.extend(first)
        transforms.extend(second)
        mid_x = _round((start_x + end_x) / 2, request.coordinate_frame.rounding)
        mid_y = _round((start_y + end_y) / 2, request.coordinate_frame.rounding)
        actions = [
            Action(kind=ActionKind.POINTER_DOWN, time_ms=0, x=start_x, y=start_y),
            Action(kind=ActionKind.POINTER_MOVE, time_ms=100, x=mid_x, y=mid_y),
            Action(kind=ActionKind.POINTER_MOVE, time_ms=200, x=end_x, y=end_y),
            Action(kind=ActionKind.POINTER_UP, time_ms=220, x=end_x, y=end_y),
        ]
    elif solution_type == SolutionType.ANGLE and solution.angle_degrees is not None:
        actions = [Action(kind=ActionKind.ROTATE, time_ms=0, angle_degrees=solution.angle_degrees)]
    elif solution_type == SolutionType.POINTS:
        for index, point in enumerate(solution.points):
            x, y, records = map_point(point.x, point.y, request.coordinate_frame)
            transforms.extend(records)
            actions.append(Action(kind=ActionKind.CLICK, time_ms=index * 100, x=x, y=y))
    else:
        raise ValueError(f"reference planner does not support solution type {solution.type}")
    prediction_hash = prediction.artifact_hash or artifact_hash(prediction)
    plan = ActionPlan(
        plan_id=f"plan-{uuid.uuid5(uuid.NAMESPACE_URL, artifact_hash({'request': request.request_id, 'prediction': prediction_hash}))}",
        challenge_instance_id=request.challenge_instance_id,
        source_prediction_id=prediction.prediction_id,
        source_prediction_hash=prediction_hash,
        input_hash=prediction.input_hash,
        session_binding_hash=request.session_binding_hash,
        target_id=request.target_id,
        planner_binding=ArtifactBinding(registry_kind="action", entry_id=PLANNER_ID, version=PLANNER_VERSION, artifact_hash=PLANNER_HASH),
        coordinate_frame=request.coordinate_frame,
        transforms=transforms,
        actions=actions,
        constraints=["first_party_local_evaluation_only", "non_executable_reference_plan"],
        stop_conditions=STOP_CONDITIONS,
        maximum_action_count=16,
        created_at=request.created_at,
        expires_at=request.expires_at,
        authorization_record_id=request.authorization_record_id,
        executable=False,
    )
    return plan
