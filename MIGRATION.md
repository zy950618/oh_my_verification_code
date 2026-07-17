# Migration to CAPTCHA Verification Skills 1.0

This repository was extracted from a broader reverse-engineering Skill collection and is now an independent, English, provider-neutral Skill suite.

## Product boundary

The repository contains two separate migration surfaces:

- a Claude Code plugin with six independently routeable governance and workflow Skills;
- a Python distribution with deterministic contracts, validation, registries, schema export, promotion evaluation, adapter scaffolding, and the `captcha-skills` CLI.

Loading one surface does not install the other. Partner-specific targets and authorization records belong in private overlays and are not distributed with the public plugin or Python package.

`1.0.0-rc.1` is a contracts and scaffolding preview. FastAPI and MCP are thin optional transports. Browser, vision, and training extras are dependency hooks for downstream/private implementations, not bundled capabilities.

## Breaking changes

- Canonical plugin/package name: `captcha-verification-skills`.
- The former Chinese layer directory is archived at `archive/legacy-skills-v0/` and is not auto-discovered.
- Ten overlapping routes are replaced by six canonical Skills. See [`migration/skill-names.yaml`](migration/skill-names.yaml).
- Runtime aliases are intentionally not provided.
- Canonical roots are:
  - `evidence/public-range`
  - `experience/skills-experience`
  - `labs/public-range-labs`
- Canonical solution offset is `offset: {x, y}`. `offset_x` is not part of v1.
- Generic `PASS` and `success` fields are replaced by orthogonal operation, prediction, execution, provider-verification, business-acceptance, and promotion states.

## Historical evidence

Historical paths are provenance. Do not replace an `origin_locator` or delete a unique evidence file. Current resolvable locations are added through `migration/legacy-locators.jsonl` and validated independently.

## Command migration

The implemented release-candidate entry points are:

```text
captcha-skills --help
captcha-skills export-schemas [OUTPUT]
captcha-skills validate ...
captcha-skills registry list
captcha-skills registry validate
captcha-skills evaluate ...
captcha-skills scaffold-target-adapter ...
```

These future-compatible command names are reserved but not implemented in `1.0.0-rc.1`:

```text
captcha-skills classify
captcha-skills solve
captcha-skills plan-action
```

Each reserved command returns `operation_status: blocked`, identifies missing implementation evidence, and exits with code `4`. The matching FastAPI routes return HTTP 501. They are contract surfaces, not migrated solver implementations.

Legacy cwd-sensitive wrappers are not the canonical interface and are not registered as Python-package capabilities.

## Acceptance semantics

A prediction, browser action, provider token, provider test key, provider verification response, or HTTP 200 does not establish protected business success. Approval requires a valid verified authorization record and a first-party business receipt with business-data assertions, repeat acceptance, and zero negative-control ledger delta.

## Rollback

Roll back by reverting the 1.0 refactor commits. Evidence and private target overlays are outside the runtime compatibility layer and must not be deleted during rollback.
