---
name: captcha-action-validation
description: Validate supplied versioned, non-executable CAPTCHA action-plan contracts, coordinate frames, typed actions, expiry, stop conditions, and supplied driver receipts. Includes a non-executable local fixture planner; it bundles no browser driver or target executor.
when_to_use: Use when an externally produced action plan or execution receipt must be checked for scope, coordinate, timing, expiry, and evidence boundaries.
license: MIT
compatibility: Requires Python 3.11+ and the captcha-verification-skills package. Authorized drivers are external; the browser extra does not add one.
argument-hint: "[prediction result and coordinate frame]"
metadata:
  owner: zhaoyang
  version: "1.0.0"
  lifecycle: governed
---

# CAPTCHA Action Validation

Validate a supplied scoped action plan. Validation is side-effect free; this RC does not bundle planning or execution.

## Release candidate boundary

Validates supplied action-plan contracts and documents the bundled non-executable local fixture planner. The `1.0.0` availability state is `local_reference_runtime_available`; no browser driver or target executor is bundled.

## Workflow

1. Validate the prediction ID, challenge instance, scope, asset freshness, and coordinate frame.
2. Validate supplied viewport, DPR, crop, iframe, scroll, and transform mappings.
3. Validate typed actions for monotonic timing, bounds, constraints, expiry, and stop conditions.
4. Return `executable: false` unless a separate executor preflight validates authorization and freshness.
5. Validate a separately supplied `ExecutionReceipt` when an external authorized driver has replayed the plan; no driver is bundled.
6. Keep provider verification and first-party business acceptance in separate receipts.
7. Return metrics and negative-control results without promoting business success.

## Output contract

- action-plan ID, source prediction ID, challenge instance, and plan hash
- coordinate frame and typed actions
- constraints, expiry, stop conditions, and authorization reference
- execution status and driver receipt when replayed
- provider-verification status if independently observed
- `business_acceptance_status: not_attempted` unless supplied by the authorized-flow gate

## Boundaries

Offline distance or angle thresholds produce local metric results, never `backend_accepted`. A successful driver call means execution completed, not that the provider or business endpoint accepted it. Plans are stale when their challenge instance, coordinate frame, or expiry no longer matches.

## References

- [Action plan contract](references/action-plan-contract.md)
- [Driver and receipt boundary](references/driver-and-receipt-boundary.md)
- [Replay negative controls](references/replay-negative-controls.md)
