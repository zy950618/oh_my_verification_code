# CAPTCHA Verification Skills — Claude Guide

This repository is an installable Skill suite, not a standalone CAPTCHA application.

## Product boundary

- Treat the namespaced Claude Code Skills under `plugin/skills/` as the primary product.
- Keep deterministic behavior in the provider-neutral Python package and `captcha-skills` CLI.
- Keep FastAPI, MCP, browser, vision, and training integrations optional and thin.
- Generate target-adapter engineering packages without executing them.
- Keep partner-specific targets and authorization evidence in private overlays or repositories.

## Evidence and authorization

- Work only with self-owned systems, local fixtures, public ranges that explicitly allow testing, official provider sandboxes/test keys, or targets covered by a validated authorization record.
- Label material claims as `observed`, `derived`, `assumed`, or `unverified`.
- Record unavailable approvals, telemetry, benchmarks, and external validation as **missing evidence**.
- A claimed or oral authorization remains `unverified` and cannot enable production execution.
- CAPTCHA success requires the final first-party protected business API receipt, business-data assertions, required repeat acceptance, and zero negative-control ledger delta.
- Challenge endpoints, provider test keys, HTTP 200, browser text, provider tokens, and model predictions are not business success.

## Canonical output and registries

- Normalized solution fields are `points`, `tiles`, `offset`, `angle_degrees`, `track`, `press`, and `text`.
- Use separate solver, model, dataset, action, target, and evidence registries.
- Use orthogonal operation, prediction, execution, provider-verification, business-acceptance, and promotion states. Do not emit a generic `PASS` as a capability decision.
- Derive CLI JSON, FastAPI models, MCP schemas, exported JSON Schema, and generated adapters from the canonical Pydantic contracts in `plugin/src/`.

## Retained boundaries

Reject or downgrade:

- unscoped third-party production CAPTCHA, WAF, or risk-control interaction;
- stealth, webdriver hiding, fingerprint spoofing, or clearance-cookie reuse;
- forged provider/risk/access-control tokens;
- promotion of `unverified` claims to `observed`;
- deletion of unique evidence without a validated migration.

Browser drivers can produce observation and execution receipts. They cannot issue first-party business-acceptance receipts or promote capabilities.

## Repository paths

- Canonical Skills: `plugin/skills/`
- Provider-neutral core: `plugin/src/captcha_verification/`
- Public evidence: `evidence/public-range/`
- Skill experience: `experience/skills-experience/`
- Public/local labs: `labs/public-range-labs/`
- Non-discoverable legacy Skills: `archive/legacy-skills-v0/`
- Migration maps: `migration/`

Historical `origin_locator` values are provenance. Add `current_locator` and `locator_status` through the migration index instead of overwriting historical evidence.

## Public repository policy

Commit specifications, source, schemas, Skills, evals, CI, and sanitized examples. Do not commit raw HAR files, cookies or tokens, browser profiles, model weights/checkpoints, private targets, unsanitized reports, production evidence, or credentials.
