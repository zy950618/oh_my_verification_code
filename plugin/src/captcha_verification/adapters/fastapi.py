from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from captcha_verification.contracts import ActionPlan, ClassificationRequest, ClassificationResult, SolveRequest


class PlanActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    prediction_id: str
    challenge_instance_id: str
    authorization_record_id: str
    width: Annotated[float, Field(gt=0)]
    height: Annotated[float, Field(gt=0)]


def create_app():
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:
        raise RuntimeError("Install captcha-verification-skills[fastapi]") from exc

    app = FastAPI(
        title="CAPTCHA Verification Skills Contract Transport",
        version="1.0.0-rc.1",
        description=(
            "Thin provider-neutral contract transport. Readiness covers this transport only; "
            "classifier, solver, and planner implementations are unavailable in this release candidate. "
            "It does not execute targets or issue business receipts."
        ),
    )

    @app.get("/health/live")
    def live() -> dict[str, object]:
        return {"status": "live", "scope": "transport"}

    @app.get("/health/ready")
    def ready() -> dict[str, object]:
        return {
            "status": "ready",
            "scope": "contract_transport",
            "capabilities": {
                "classifier": "unavailable",
                "solver": "unavailable",
                "planner": "unavailable",
            },
        }

    @app.post("/classify", response_model=ClassificationResult)
    def classify(request: ClassificationRequest) -> ClassificationResult:
        raise HTTPException(status_code=501, detail={"code": "classifier_unavailable", "request_id": request.request_id})

    @app.post("/solve")
    def solve(request: SolveRequest) -> dict[str, object]:
        raise HTTPException(status_code=501, detail={"code": "solver_unavailable", "request_id": request.request_id})

    @app.post("/plan-action", response_model=ActionPlan)
    def plan_action(request: PlanActionRequest) -> ActionPlan:
        raise HTTPException(status_code=501, detail={"code": "planner_unavailable", "request_id": request.request_id})

    return app


app = create_app()
