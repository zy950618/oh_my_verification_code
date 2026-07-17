from __future__ import annotations

from captcha_verification.adapters.mcp import create_server


def test_mcp_exposes_read_only_local_runtime_tools() -> None:
    server = create_server()
    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}
    assert set(tools) == {
        "captcha_get_registry_entry",
        "captcha_classify_local_fixture",
        "captcha_solve_local_fixture",
        "captcha_plan_local_action",
        "captcha_scaffold_adapter",
    }
    assert all(tool.annotations.readOnlyHint is True for tool in tools.values())
    assert all(tool.annotations.idempotentHint is True for tool in tools.values())
    assert all(tool.annotations.openWorldHint is False for tool in tools.values())
    assert all("execute" not in name and "business" not in name and "receipt" not in name for name in tools)
    instructions = server.instructions.lower()
    assert "local fixture classification" in instructions
    assert "no target execution or receipt signing" in instructions
