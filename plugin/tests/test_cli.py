from __future__ import annotations

import json
from pathlib import Path

import pytest

from captcha_verification.cli import main


def test_cli_exports_schemas(tmp_path: Path, capsys) -> None:
    code = main(["export-schemas", str(tmp_path)])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["operation_status"] == "succeeded"
    assert list(tmp_path.glob("*.schema.json"))


def test_cli_scaffold_defaults_to_dry_run(tmp_path: Path, capsys) -> None:
    output = tmp_path / "private" / "targets" / "owned-target"
    code = main(
        [
            "scaffold-target-adapter",
            "--target-id",
            "owned-target",
            "--challenge-family",
            "slider",
            "--output-root",
            str(output),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["result"]["execution_status"] == "not_run"
    assert payload["result"]["write_mode"] is False
    assert payload["result"]["written_paths"] == []
    assert payload["warnings"] == ["dry-run only; no files were written"]
    assert payload["result"]["files"]
    assert all(file["sha256"] for file in payload["result"]["files"])
    assert not output.exists()


@pytest.mark.parametrize("command", ["classify", "solve", "plan-action"])
def test_runtime_operations_require_a_local_request_file(command: str, capsys) -> None:
    code = main([command])
    payload = json.loads(capsys.readouterr().out)

    assert code == 4
    assert payload["operation_status"] == "blocked"
    assert payload["result"] == {"command": command}
    assert payload["missing_evidence"] == ["local fixture request file is required"]
    assert payload["errors"] == []
