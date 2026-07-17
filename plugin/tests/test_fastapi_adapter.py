from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from captcha_verification.adapters.fastapi import app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as value:
        yield value


@pytest.mark.anyio
async def test_fastapi_health_is_local_runtime_scoped(client: httpx.AsyncClient) -> None:
    assert (await client.get("/health/live")).json() == {"status": "live", "scope": "transport"}
    assert (await client.get("/health/ready")).json() == {
        "status": "ready",
        "scope": "local_fixture_reference_runtime",
        "capabilities": {
            "classifier": "local_fixture_only",
            "solver": "slider_rotate_click_local_fixture_only",
            "planner": "non_executable_local_plan_only",
        },
    }
    schema = app.openapi()
    assert "repository-owned raster fixtures" in schema["info"]["description"]
    assert {"/classify", "/solve", "/plan-action"} <= set(schema["paths"])
    assert all("execute" not in path and "receipt" not in path for path in schema["paths"])


@pytest.mark.anyio
async def test_fastapi_classify_fails_closed_without_authorization(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/classify",
        json={
            "request_id": "request-classify",
            "assets": [{"asset_id": "asset-1", "uri": "file:///fixture.png", "media_type": "image/png", "sha256": "abc"}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unsupported"
    assert payload["challenge_family"] == "unknown"
    assert payload["authorization_decision"] == "missing_verified_authorization"
