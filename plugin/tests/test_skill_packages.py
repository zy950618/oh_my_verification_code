from __future__ import annotations

import json
from pathlib import Path

import yaml


def test_skill_packages_are_portable_and_references_exist() -> None:
    root = Path(__file__).resolve().parents[1] / "skills"
    packages = sorted(path for path in root.iterdir() if path.is_dir())
    assert len(packages) == 6

    for package in packages:
        text = (package / "SKILL.md").read_text(encoding="utf-8")
        _, frontmatter, body = text.split("---", 2)
        metadata = yaml.safe_load(frontmatter)
        assert metadata["name"] == package.name
        assert metadata["description"]
        for forbidden in ("triggers", "platforms", "category", "standard_type", "version"):
            assert forbidden not in metadata
        assert len(text.splitlines()) < 500
        assert "## Release candidate boundary" in body
        assert "## Output contract" in body
        assert "## References" in body

        interface = yaml.safe_load((package / "agents" / "interface.yaml").read_text(encoding="utf-8"))
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        route_eval = yaml.safe_load((package / "evals" / "route-baseline.yaml").read_text(encoding="utf-8"))
        evals = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted((package / "evals").glob("*.yaml"))]
        assert evals
        for evaluation in evals:
            assert evaluation["id"]
            assert evaluation["skill"] == package.name
            assert evaluation["expected"]
        assert interface["name"] == package.name
        assert manifest["name"] == package.name
        assert manifest["input_files"] == "file-backed fixture"
        assert manifest["output_contract"]
        assert manifest["rollback_boundary"]

        boundary = manifest["release_candidate_boundary"]
        assert interface["release_candidate_boundary"] == {
            "availability": boundary["availability"],
            "generated_artifacts": boundary["generated_artifacts"],
        }
        assert route_eval["expected"]["release_candidate_availability"] == boundary["availability"]
        assert route_eval["expected"]["generated_artifacts"] == boundary["generated_artifacts"]

        if package.name == "captcha-adapter-scaffolding":
            assert boundary["availability"] == "available_generate_only"
            assert boundary["generated_artifacts"] == "generated_not_executed"
            assert "never imports" in body
        else:
            assert boundary["availability"] == "local_reference_runtime_available"
            assert boundary["generated_artifacts"] == "not_applicable"

        for reference in (package / "references").glob("*.md"):
            assert f"references/{reference.name}" in text
