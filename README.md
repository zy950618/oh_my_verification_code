# CAPTCHA Verification Skills

An installable, provider-neutral Skill suite for authorized CAPTCHA and verification-service engineering.

## 1.0.0 release-candidate boundary

`1.0.0-rc.1` is a contracts, governance, validation, and adapter-scaffolding preview. It does not bundle classifier, solver, action-planner, browser-driver, provider-diagnostics, or model-training implementations.

The implemented `captcha-skills` commands are:

- `validate`
- `registry`
- `evaluate`
- `export-schemas`
- `scaffold-target-adapter`

`classify`, `solve`, and `plan-action` reserve the future command surface. In this release candidate they fail closed with `operation_status: blocked` and exit code `4`. The corresponding FastAPI operations return HTTP 501.

## Product shape

The repository produces two separate artifacts:

1. The Claude Code plugin under `plugin/`, which provides six independently routeable governance and workflow Skills.
2. The Python distribution under `plugin/`, which provides canonical Pydantic contracts, validation, registries, schema export, promotion evaluation, adapter scaffolding, and the `captcha-skills` CLI.

Loading the Claude plugin does not install the Python distribution, and installing the Python distribution does not install the Claude Skills. Local development that uses both surfaces must load and install them separately.

The six Skills are:

- `captcha-authorized-flow`
- `captcha-provider-diagnostics`
- `captcha-solver-core`
- `captcha-model-lifecycle`
- `captcha-action-validation`
- `captcha-adapter-scaffolding`

## Scope

Supported work includes local fixtures, self-owned systems, official provider sandboxes/test keys, public ranges that explicitly allow testing, and targets covered by a validated authorization record.

A CAPTCHA capability claim requires evidence from the final first-party protected business API. Challenge endpoints, provider test keys, HTTP 200, browser text, model output, and provider verification alone are not business success.

The suite does not provide generic support for stealth, webdriver hiding, fingerprint spoofing, clearance-cookie reuse, forged risk tokens, or unscoped third-party production interaction.

## Install the Python core

```bash
python -m pip install -e ./plugin
captcha-skills --help
```

Optional extras are installed explicitly:

```bash
python -m pip install -e './plugin[fastapi]'
python -m pip install -e './plugin[mcp]'
python -m pip install -e './plugin[browser]'
python -m pip install -e './plugin[vision]'
python -m pip install -e './plugin[train]'
```

The FastAPI and MCP extras enable thin contract transports. The browser, vision, and train extras provide dependency hooks for downstream or private implementations; they do not add bundled operational implementations in this release candidate.

## Load the Claude Code plugin

For local development:

```bash
claude --plugin-dir ./plugin
```

Validate before release:

```bash
claude plugin validate ./plugin --strict
```

Installed Skills are namespaced, for example:

```text
/captcha-verification-skills:captcha-provider-diagnostics
/captcha-verification-skills:captcha-adapter-scaffolding
```

## Repository layout

| Path | Purpose |
|---|---|
| `plugin/.claude-plugin/` | Claude Code plugin manifest |
| `plugin/skills/` | Canonical English Skill packages |
| `plugin/src/captcha_verification/` | Provider-neutral Python core and CLI |
| `plugin/src/captcha_verification/templates/` | Generate-only target-adapter templates |
| `plugin/schemas/` | Exported machine contracts |
| `plugin/tests/` | Python contract, boundary, and package-structure tests |
| `evidence/` | Sanitized evidence and manifests |
| `experience/` | Historical failure and experience records |
| `datasets/` | Dataset manifests and metadata; no raw data or weights |
| `labs/` | Self-owned and public-range fixtures |
| `archive/legacy-skills-v0/` | Non-discoverable legacy Skills retained for migration evidence |
| `migration/` | Name, path, and historical locator mappings |
| `reports/` | Trust and output-quality release records |

## Private targets

A natural-language target request generates a versioned adapter engineering package. It does not execute the target. Partner-specific adapters, authorization evidence, credentials, raw captures, and business assertions must be stored in a private repository or ignored `private/targets/` overlay.

## Fact levels

Every material conclusion uses one of:

- `observed`
- `derived`
- `assumed`
- `unverified`

Unavailable approvals, telemetry, benchmarks, or external validation are recorded as **missing evidence**.

## Migration

See [MIGRATION.md](MIGRATION.md) and [migration/skill-names.yaml](migration/skill-names.yaml).

## Public repository policy

Commit specifications, source, schemas, Skills, evals, CI, and sanitized minimal examples. Do not commit raw HAR files, cookies or tokens, browser profiles, model weights/checkpoints, private targets, unsanitized evidence, production credentials, timestamped run outputs, repeat reports, or authorized-live observations. Large dataset manifests, failure-card batches, and evaluation outputs are reproducible or archived outside the public repository; the repository keeps only canonical small fixtures needed for validation.
