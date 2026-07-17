---
name: captcha-authorized-flow
description: Validate supplied authorization and receipt contracts for a CAPTCHA or verification-service workflow. Use for authorization review, provider-to-business flow mapping, missing-evidence analysis, or a promotion decision. This release candidate does not collect receipts or execute targets.
when_to_use: Use for supplied authorization records, protected business API receipts, repeat verification evidence, promotion decisions, and cross-stage governance. Runtime handoffs require external implementations.
license: MIT
compatibility: Requires Python 3.11+ and the captcha-verification-skills package. Target execution is not bundled with this skill.
argument-hint: "[scope record or authorized workflow description]"
disable-model-invocation: true
metadata:
  owner: zhaoyang
  version: "1.0.0-rc.1"
  lifecycle: governed
---

# CAPTCHA Authorized Flow

Use this skill as the explicit, governed entry point for an authorized verification workflow. It coordinates other suite skills but does not implement provider-specific bypass behavior or execute a target automatically.

## Release candidate boundary

Validates supplied authorization and receipt contracts; it does not collect receipts or execute targets. The `1.0.0-rc.1` availability state is `blocked_without_external_implementation`.

## Workflow

1. Read [Authorization and scope](references/authorization-and-scope.md).
2. Validate the authorization record, target environment, allowed hosts, routes, methods, actions, validity window, retention policy, and operator acknowledgement.
3. If the task is provider observation, hand off to `captcha-provider-diagnostics`.
4. If the task requires a prediction, hand off to `captcha-solver-core`.
5. If the task requires an action artifact, hand off to `captcha-action-validation`.
6. Validate separately supplied execution, provider-verification, and first-party business-acceptance receipts; record absent receipts as missing evidence.
7. Apply [Outcome and evidence gate](references/outcome-and-evidence-gate.md).
8. Return the output contract below. Never promote missing evidence.

## Output contract

Return a structured result containing:

- `operation_status`
- authorization and scope decisions
- provider flow and site binding
- evidence references and fact claims (`observed`, `derived`, `assumed`, `unverified`)
- execution, provider verification, and business acceptance statuses
- business-data and repeat-gate assertions
- promotion decision and blockers

`business_acceptance_status: accepted` requires a valid verified authorization record, an accepted first-party protected business endpoint receipt, matching ledger/ownership/version assertions, a required fresh repeat acceptance, and zero ledger delta for negative controls.

## Boundaries

- HTTP 200, challenge success, provider test keys, model confidence, browser text, or token generation are not business acceptance.
- A claimed or oral authorization remains `unverified`; it cannot enable production execution.
- This skill does not produce stealth, webdriver hiding, fingerprint spoofing, clearance-cookie reuse, forged risk tokens, or generic third-party production presets.
- If a visible challenge requires a person, return a human-review handoff and preserve the incomplete evidence state.

## References

- [Authorization and scope](references/authorization-and-scope.md)
- [Outcome and evidence gate](references/outcome-and-evidence-gate.md)
- [Target adapter boundary](references/target-adapter-boundary.md)
