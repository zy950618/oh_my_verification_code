from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from captcha_verification.adapters.fastapi import app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as value:
        yield value


@pytest.mark.anyio
async def test_fastapi_health_is_transport_scoped(client: httpx.AsyncClient) -> None:
    assert (await client.get("/health/live")).json() == {"status": "live", "scope": "transport"}
    assert (await client.get("/health/ready")).json() == {
        "status": "ready",
        "scope": "contract_transport",
        "capabilities": {
            "classifier": "unavailable",
            "solver": "unavailable",
            "planner": "unavailable",
        },
    }

    schema = app.openapi()
    assert "Readiness covers this transport only" in schema["info"]["description"]
    paths = schema["paths"]
    assert {"/classify", "/solve", "/plan-action"} <= set(paths)
    assert all("execute" not in path and "run-target" not in path for path in paths)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "payload", "code"),
    [
        (
            "/classify",
            {
                "request_id": "request-classify",
                "assets": [
                    {
                        "asset_id": "asset-1",
                        "uri": "file:///fixture.png",
                        "media_type": "image/png",
                        "sha256": "abc",
                    }
                ],
            },
            "classifier_unavailable",
        ),
        (
            "/solve",
            {
                "request_id": "request-solve",
                "challenge_instance_id": "challenge-1",
                "challenge_family": "slider",
                "allowed_solution_types": ["offset"],
                "assets": [
                    {
                        "asset_id": "asset-1",
                        "uri": "file:///fixture.png",
                        "media_type": "image/png",
                        "sha256": "abc",
                    }
                ],
            },
            "solver_unavailable",
        ),
        (
            "/plan-action",
            {
                "request_id": "request-plan",
                "prediction_id": "prediction-1",
                "challenge_instance_id": "challenge-1",
                "authorization_record_id": "authorization-1",
                "width": 100,
                "height": 50,
            },
            "planner_unavailable",
        ),
    ],
)
async def test_fastapi_operations_fail_closed(
    client: httpx.AsyncClient,
    path: str,
    payload: dict[str, object],
    code: str,
) -> None:
    response = await client.post(path, json=payload)
    assert response.status_code == 501
    detail = response.json()["detail"]
    assert detail == {"code": code, "request_id": payload["request_id"]}
