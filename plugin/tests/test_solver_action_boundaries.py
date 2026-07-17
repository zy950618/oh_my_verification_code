from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from captcha_verification.contracts import Action, ActionPlan, CoordinateFrame, NormalizedSolution, PredictionOutcome


def test_prediction_cannot_claim_business_acceptance() -> None:
    with pytest.raises(ValueError):
        PredictionOutcome(
            prediction_id="prediction-1",
            request_id="request-1",
            challenge_instance_id="challenge-1",
            status="produced",
            solution=NormalizedSolution(type="offset", offset={"x": 10, "y": 0}),
            confidence=0.9,
            solver_id="solver",
            solver_version="1",
            input_hash="sha256",
            business_acceptance_status="accepted",
        )


def test_action_plan_is_non_executable_and_validates_bounds() -> None:
    now = datetime.now(timezone.utc)
    plan = ActionPlan(
        plan_id="plan-1",
        challenge_instance_id="challenge-1",
        source_prediction_id="prediction-1",
        coordinate_frame=CoordinateFrame(width=100, height=100, device_pixel_ratio=2),
        actions=[Action(kind="click", time_ms=0, x=50, y=50)],
        stop_conditions=["provider rejection", "challenge drift"],
        created_at=now,
        expires_at=now + timedelta(seconds=30),
        authorization_record_id="auth-1",
    )
    assert plan.executable is False

    with pytest.raises(ValueError, match="outside"):
        ActionPlan(
            plan_id="plan-2",
            challenge_instance_id="challenge-1",
            source_prediction_id="prediction-1",
            coordinate_frame=CoordinateFrame(width=100, height=100, device_pixel_ratio=1),
            actions=[Action(kind="click", time_ms=0, x=101, y=50)],
            stop_conditions=["reject"],
            created_at=now,
            expires_at=now + timedelta(seconds=30),
            authorization_record_id="auth-1",
        )
