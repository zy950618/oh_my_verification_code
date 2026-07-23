from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

from captcha_verification.contracts.export import export_schemas


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILLS = {
    "captcha-action-validation",
    "captcha-adapter-scaffolding",
    "captcha-authorized-flow",
    "captcha-model-lifecycle",
    "captcha-provider-diagnostics",
    "captcha-solver-core",
}


def test_skill_migration_covers_archive_without_runtime_aliases() -> None:
    migration = yaml.safe_load((ROOT / "migration" / "skill-names.yaml").read_text(encoding="utf-8"))
    assert migration["schema_version"] == "skill-migration/v1"
    assert migration["introduced_in"] == "1.0.0-rc.1"
    assert migration["runtime_aliases"] is False

    mappings = migration["mappings"]
    old_names = [mapping["old_name"] for mapping in mappings]
    assert len(old_names) == len(set(old_names)) == 10
    archived = {path.name for path in (ROOT / "archive" / "legacy-skills-v0").iterdir() if path.is_dir()}
    assert set(old_names) == archived
    mapped_skills = {mapping["new_name"] for mapping in mappings}
    assert mapped_skills == CANONICAL_SKILLS - {"captcha-adapter-scaffolding"}
    assert "captcha-adapter-scaffolding" not in mapped_skills
    assert {path.name for path in (ROOT / "plugin" / "skills").iterdir() if path.is_dir()} == CANONICAL_SKILLS
    assert all(mapping["behavior_change"] for mapping in mappings)


def test_legacy_locator_index_resolves_and_matches_content() -> None:
    seen: set[str] = set()
    path = ROOT / "migration" / "legacy-locators.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert records

    for record in records:
        assert record["schema_version"] == "legacy-locator-index/v1"
        assert record["locator_status"] in {"resolved", "archived_external"}
        assert isinstance(record["reference_count"], int) and record["reference_count"] >= 0
        assert "preserve embedded origin locators" in record["migration_policy"]

        locator = record["current_locator"]
        assert locator.startswith("repo://")
        relative = Path(locator.removeprefix("repo://"))
        assert not relative.is_absolute()
        assert ".." not in relative.parts
        assert locator not in seen
        seen.add(locator)

        current = ROOT / relative
        if record["locator_status"] == "resolved":
            assert current.is_file(), locator
            assert hashlib.sha256(current.read_bytes()).hexdigest() == record["content_sha256"], locator
        else:
            archive_locator = record.get("archive_locator", "")
            assert archive_locator.startswith("external://")


def test_committed_schemas_match_canonical_export(tmp_path: Path) -> None:
    export_schemas(tmp_path)
    committed = ROOT / "plugin" / "schemas" / "v1"
    generated_names = {path.name for path in tmp_path.glob("*.schema.json")}
    committed_names = {path.name for path in committed.glob("*.schema.json")}
    assert generated_names == committed_names
    for name in generated_names:
        assert (tmp_path / name).read_bytes() == (committed / name).read_bytes(), name


def test_current_release_markdown_links_resolve() -> None:
    markdown_files = [
        ROOT / "README.md",
        ROOT / "MIGRATION.md",
        ROOT / "plugin" / "README.md",
        *(ROOT / "reports").glob("*.md"),
        *(ROOT / "plugin" / "skills").glob("**/*.md"),
    ]
    link_pattern = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")

    for source in markdown_files:
        text = source.read_text(encoding="utf-8")
        for raw_target in link_pattern.findall(text):
            target = raw_target.split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (source.parent / target).resolve()
            assert resolved == ROOT or ROOT in resolved.parents, f"link escapes repository: {source}: {target}"
            assert resolved.exists(), f"broken link: {source}: {target}"
