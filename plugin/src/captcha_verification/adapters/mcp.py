from __future__ import annotations

from pathlib import Path

from captcha_verification.registries import DEFAULT_REGISTRY
from captcha_verification.services import ScaffoldSpec, build_scaffold


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install captcha-verification-skills[mcp]") from exc

    server = FastMCP(
        "captcha-verification-skills",
        instructions=(
            "Provider-neutral registry inspection and target-adapter scaffold dry-run tools. "
            "No classifier, solver, planner, driver, or business-receipt capability is bundled, "
            "and no tool writes files or executes a target."
        ),
    )

    @server.tool(
        name="captcha_get_registry_entry",
        description="Read a versioned provider-neutral registry entry. Call this before selecting an existing solver, model, dataset, action, or target capability.",
        annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    )
    def get_registry_entry(entry_type: str, entry_id: str, version: str | None = None) -> dict[str, object]:
        return DEFAULT_REGISTRY.get(entry_type, entry_id, version).model_dump(mode="json")

    @server.tool(
        name="captcha_scaffold_adapter",
        description="Dry-run a private target-adapter scaffold. Call this when a user asks to generate an authorized target interface. It returns proposed files and never writes, navigates, or calls a driver.",
        annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    )
    def scaffold_adapter(target_id: str, challenge_family: str, transports: list[str] | None = None) -> dict[str, object]:
        package_root = Path(__file__).resolve().parents[1]
        spec = ScaffoldSpec(
            target_id=target_id,
            challenge_family=challenge_family,
            transports=transports or ["cli"],
        )
        result = build_scaffold(
            spec,
            template_root=package_root / "templates" / "target-adapter",
            output_root=Path("private") / "targets" / target_id,
        )
        return result.as_dict()

    return server


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
