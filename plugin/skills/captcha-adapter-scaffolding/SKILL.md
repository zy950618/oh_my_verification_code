---
name: captcha-adapter-scaffolding
description: Generate a versioned, auditable, testable private target-adapter project from a scoped natural-language request. Use when a user asks to create an interface skeleton for an authorized target or CAPTCHA family. This skill generates files and validation reports only; it never visits, tests, or executes the target.
when_to_use: Use for one-sentence target interface requests, adapter manifests, authorization placeholders, capability declarations, transport stubs, and conformance tests. Do not use to run an adapter or claim target compatibility.
license: MIT
compatibility: Requires Python 3.11+ and the captcha-verification-skills package. Generated partner targets belong in an ignored private overlay.
argument-hint: "[target-id] [challenge-family] [cli|fastapi|mcp]"
disable-model-invocation: true
metadata:
  owner: zhaoyang
  version: "1.0.0"
  lifecycle: governed
---

# CAPTCHA Adapter Scaffolding

Generate an adapter engineering package without interacting with the target.

## Release candidate boundary

Deterministically generates or previews private adapter files; generated files are never executed. The `1.0.0` availability state is `available_generate_only`.

## Workflow

1. Parse the request into a target ID, challenge family, requested transports, and known authorization metadata.
2. Read [Generated adapter contract](references/generated-adapter-contract.md).
3. Validate identifiers and reject path traversal or public output for partner-specific details.
4. Run `captcha-skills scaffold-target-adapter ...` in dry-run mode first.
5. Present the planned paths and missing evidence.
6. After explicit approval to write, generate the private overlay.
7. Run static generated-package validation only.
8. Return artifact IDs, path diff, validation report, and next evidence requirements.

## Output contract

- generator and template versions
- request hash and target ID
- output visibility and root
- generated path list and content hashes
- validation status
- authorization and provider facts with missing evidence
- `execution_status: not_run`
- next required steps before any driver preflight

## Boundaries

The generator never imports or calls a browser driver, opens a network connection, loads credentials, navigates to the target, fabricates a provider token, or claims the generated adapter works. It does not produce stealth, webdriver hiding, fingerprint spoofing, or clearance behavior.

## References

- [Generated adapter contract](references/generated-adapter-contract.md)
- [Private overlay policy](references/private-overlay-policy.md)
- [Generated adapter test matrix](references/generated-adapter-test-matrix.md)
