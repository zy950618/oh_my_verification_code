from __future__ import annotations

from pathlib import Path

from captcha_verification.actions import plan_action
from captcha_verification.classification import classify
from captcha_verification.contracts import ClassificationRequest, PlanActionRequest, SolveRequest
from captcha_verification.registries import DEFAULT_REGISTRY
from captcha_verification.services import ScaffoldSpec, build_scaffold
from captcha_verification.solvers import solve


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install captcha-verification-skills[mcp]") from exc

    server = FastMCP(
        "captcha-verification-skills",
        instructions=(
            "Read-only provider-neutral local fixture classification, solving, non-executable planning, "
            "registry inspection, and adapter scaffold dry-runs. No target execution or receipt signing."
        ),
    )

    @server.tool(name="captcha_get_registry_entry", description="Read a versioned provider-neutral registry entry.", annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
    def get_registry_entry(entry_type: str, entry_id: str, version: str | None = None) -> dict[str, object]:
        return DEFAULT_REGISTRY.get(entry_type, entry_id, version).model_dump(mode="json")

    @server.tool(name="captcha_classify_local_fixture", description="Classify one authorized repository-owned raster fixture.", annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
    def classify_local_fixture(request: dict[str, object]) -> dict[str, object]:
        return classify(ClassificationRequest.model_validate(request)).model_dump(mode="json")

    @server.tool(name="captcha_solve_local_fixture", description="Solve one classified local slider, rotate, or click fixture.", annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
    def solve_local_fixture(request: dict[str, object]) -> dict[str, object]:
        return solve(SolveRequest.model_validate(request)).model_dump(mode="json")

    @server.tool(name="captcha_plan_local_action", description="Produce a non-executable action plan for a local fixture prediction.", annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
    def plan_local_action(request: dict[str, object]) -> dict[str, object]:
        return plan_action(PlanActionRequest.model_validate(request)).model_dump(mode="json")

    @server.tool(name="captcha_scaffold_adapter", description="Dry-run a private target-adapter scaffold without writing or executing it.", annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
    def scaffold_adapter(target_id: str, challenge_family: str, transports: list[str] | None = None) -> dict[str, object]:
        package_root = Path(__file__).resolve().parents[1]
        spec = ScaffoldSpec(target_id=target_id, challenge_family=challenge_family, transports=transports or ["cli"])
        result = build_scaffold(spec, template_root=package_root / "templates" / "target-adapter", output_root=Path("private") / "targets" / target_id)
        return result.as_dict()

    return server


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
