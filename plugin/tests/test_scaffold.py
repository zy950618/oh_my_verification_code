from __future__ import annotations

from pathlib import Path

import pytest

from captcha_verification.services import ScaffoldSpec, build_scaffold, write_scaffold


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "src" / "captcha_verification" / "templates" / "target-adapter"


def test_scaffold_is_deterministic_and_generate_only(tmp_path: Path) -> None:
    spec = ScaffoldSpec(target_id="owned-target", challenge_family="slider", transports=["mcp", "cli"])
    output = tmp_path / "private" / "targets" / spec.target_id
    first = build_scaffold(spec, template_root=TEMPLATE_ROOT, output_root=output)
    second = build_scaffold(spec, template_root=TEMPLATE_ROOT, output_root=output)

    assert first.request_hash == second.request_hash
    assert [(file.path, file.sha256) for file in first.files] == [(file.path, file.sha256) for file in second.files]
    assert first.status == "generated_not_executed"
    assert not output.exists()


def test_scaffold_write_stays_inside_private_target(tmp_path: Path) -> None:
    spec = ScaffoldSpec(target_id="owned-target", challenge_family="rotate")
    output = tmp_path / "private" / "targets" / spec.target_id
    result = build_scaffold(spec, template_root=TEMPLATE_ROOT, output_root=output)
    paths = write_scaffold(result)

    assert paths
    assert all(output.resolve() in path.parents for path in paths)
    assert (output / "scaffold-manifest.json").is_file()
    assert "generated_not_executed" in (output / "scaffold-manifest.json").read_text()


def test_scaffold_rejects_public_or_traversal_output(tmp_path: Path) -> None:
    spec = ScaffoldSpec(target_id="owned-target", challenge_family="click")
    with pytest.raises(ValueError, match="private"):
        build_scaffold(spec, template_root=TEMPLATE_ROOT, output_root=tmp_path / "public" / spec.target_id)
    with pytest.raises(ValueError, match="target ID"):
        build_scaffold(spec, template_root=TEMPLATE_ROOT, output_root=tmp_path / "private" / "other")


def test_scaffold_rejects_malformed_identifiers() -> None:
    with pytest.raises(ValueError):
        ScaffoldSpec(target_id="../../escape", challenge_family="slider")
