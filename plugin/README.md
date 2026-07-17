# CAPTCHA Verification Skills

This directory is both the Claude Code plugin source and the Python distribution source for the provider-neutral CAPTCHA Verification Skills release candidate.

## 1.0.0 local reference boundary

`1.0.0` provides governance/workflow Skills, Pydantic contracts, validation, versioned registries, schema export, promotion evaluation, generate-only target-adapter scaffolding, and a deterministic local Reference Runtime for repository-owned synthetic raster fixtures. The runtime classifies and solves reference slider/rotate/click fixtures and creates typed non-executable action plans. A self-owned localhost harness closes the receipt chain through first-party business-data assertions and fresh repeat acceptance. It does not fetch or execute external targets, provide stealth, or claim third-party CAPTCHA capability.

Implemented CLI commands include `classify`, `solve`, `plan-action`, and `e2e-local` in addition to `validate`, `registry`, `evaluate`, `export-schemas`, and `scaffold-target-adapter`. The three runtime commands require file-backed local fixture requests and fail closed for unsupported, unverified, low-confidence, or external inputs.

## Two installation surfaces

### Python distribution

From this directory:

```bash
python -m pip install -e .
captcha-skills --help
```

Optional extras:

```bash
python -m pip install -e '.[fastapi]'
python -m pip install -e '.[mcp]'
python -m pip install -e '.[browser]'
python -m pip install -e '.[vision]'
python -m pip install -e '.[train]'
```

FastAPI and MCP enable thin contract transports over the same local fixture classifier, solvers, and non-executable planner. Browser and train remain dependency hooks for downstream or private implementations; installing them does not add target execution. The localhost receipt-chain harness is intentionally CLI/Python-only so transports cannot issue first-party business receipts.

### Claude Code plugin

From this directory:

```bash
claude --plugin-dir .
claude plugin validate . --strict
```

Loading this plugin exposes six independently routeable Skills:

- `captcha-authorized-flow`
- `captcha-provider-diagnostics`
- `captcha-solver-core`
- `captcha-model-lifecycle`
- `captcha-action-validation`
- `captcha-adapter-scaffolding`

Examples:

```text
/captcha-verification-skills:captcha-provider-diagnostics
/captcha-verification-skills:captcha-adapter-scaffolding
```

Installing the Python distribution does not install the Claude Skills, and loading the plugin does not install the Python distribution.

## Distribution contents

| Path | Purpose |
|---|---|
| `.claude-plugin/` | Claude Code plugin manifest |
| `skills/` | Canonical Skill packages |
| `src/captcha_verification/` | Provider-neutral Python core and CLI |
| `src/captcha_verification/templates/` | Generate-only target-adapter templates |
| `schemas/` | Exported machine contracts |
| `tests/` | Python contract, boundary, and package-structure tests |

The repository root also contains governance and provenance assets under `../archive/`, `../evidence/`, `../experience/`, `../migration/`, and `../reports/`. They are not Python wheel contents.

## Scope and evidence

Supported work is limited to local fixtures, self-owned systems, official provider sandboxes/test keys, public ranges that explicitly allow testing, and targets covered by a validated authorization record.

A CAPTCHA capability claim requires evidence from the final first-party protected business API. Challenge endpoints, provider test keys, HTTP 200, browser text, model output, and provider verification alone are not business success.

Every material conclusion uses `observed`, `derived`, `assumed`, or `unverified`. Unavailable approvals, telemetry, benchmarks, implementations, or external validation are **missing evidence**.

The suite does not provide stealth, webdriver hiding, fingerprint spoofing, clearance-cookie reuse, forged risk tokens, or unscoped third-party production interaction.

## Private targets

Target requests generate versioned adapter engineering packages. Generated files are not imported, executed, navigated, or compatibility-tested. Partner-specific adapters, authorization evidence, credentials, raw captures, and business assertions belong in a private repository or ignored `private/targets/` overlay.

## Migration

Repository checkouts should use [../MIGRATION.md](../MIGRATION.md) and [../migration/skill-names.yaml](../migration/skill-names.yaml). These repository-relative links are not bundled governance assets in the Python wheel.

## Public repository policy

Commit specifications, source, schemas, Skills, evals, CI, and sanitized minimal examples. Do not commit raw HAR files, cookies or tokens, browser profiles, model weights/checkpoints, private targets, unsanitized evidence, or production credentials.
