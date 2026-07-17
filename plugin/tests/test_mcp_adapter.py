from __future__ import annotations

from captcha_verification.adapters.mcp import create_server


def test_mcp_exposes_read_only_core_tools_only() -> None:
    server = create_server()
    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}
    assert set(tools) == {"captcha_get_registry_entry", "captcha_scaffold_adapter"}
    assert all(
        forbidden not in name
        for name in tools
        for forbidden in ("classify", "solve", "plan", "execute", "business")
    )

    instructions = server.instructions.lower()
    assert "registry inspection" in instructions
    assert "scaffold dry-run" in instructions
    assert "no classifier, solver, planner, driver" in instructions
    assert "prediction-only" not in instructions

    scaffold = tools["captcha_scaffold_adapter"]
    assert scaffold.annotations.readOnlyHint is True
    assert scaffold.annotations.idempotentHint is True
    assert scaffold.annotations.openWorldHint is False
    assert "Dry-run" in scaffold.description
    assert "never writes, navigates, or calls a driver" in scaffold.description
