from __future__ import annotations

from captcha_verification.actions import plan_action as plan_action_service
from captcha_verification.classification import classify as classify_service
from captcha_verification.contracts import (
    ActionPlan,
    ClassificationRequest,
    ClassificationResult,
    PlanActionRequest,
    PredictionOutcome,
    SolveRequest,
)
from captcha_verification.solvers import solve as solve_service


def create_app():
    try:
        from fastapi import FastAPI
    except ImportError as exc:
        raise RuntimeError("Install captcha-verification-skills[fastapi]") from exc

    app = FastAPI(
        title="CAPTCHA Verification Skills Local Reference Transport",
        version="1.0.0",
        description=(
            "Thin provider-neutral transport for repository-owned raster fixtures. "
            "It does not execute targets or issue first-party business receipts."
        ),
    )

    @app.get("/health/live")
    def live() -> dict[str, object]:
        return {"status": "live", "scope": "transport"}

    @app.get("/health/ready")
    def ready() -> dict[str, object]:
        return {
            "status": "ready",
            "scope": "local_fixture_reference_runtime",
            "capabilities": {
                "classifier": "local_fixture_only",
                "solver": "slider_rotate_click_local_fixture_only",
                "planner": "non_executable_local_plan_only",
            },
        }

    @app.post("/classify", response_model=ClassificationResult)
    def classify(request: ClassificationRequest) -> ClassificationResult:
        return classify_service(request)

    @app.post("/solve", response_model=PredictionOutcome)
    def solve(request: SolveRequest) -> PredictionOutcome:
        return solve_service(request)

    @app.post("/plan-action", response_model=ActionPlan)
    def plan_action(request: PlanActionRequest) -> ActionPlan:
        return plan_action_service(request)

    return app


app = create_app()
