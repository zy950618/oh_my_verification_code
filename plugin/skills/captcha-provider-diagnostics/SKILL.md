---
name: captcha-provider-diagnostics
description: Analyze supplied local, official-test, self-owned, or explicitly authorized evidence for provider candidates, challenge family, site binding, and provider-versus-business API boundaries. This release candidate does not browse, probe, or run a classifier.
when_to_use: Use when supplied evidence must be analyzed for provider or challenge-family candidates, integration-field drift, or provider-versus-business endpoint separation.
license: MIT
compatibility: Requires Python 3.11+ and the captcha-verification-skills package. Browser observation is an optional, separately authorized adapter.
argument-hint: "[asset path or scoped observation description]"
metadata:
  owner: zhaoyang
  version: "1.0.0"
  lifecycle: library
---

# CAPTCHA Provider Diagnostics

Diagnose provider and flow evidence without executing a challenge.

## Release candidate boundary

Analyzes supplied authorized evidence; it does not browse, probe, or run a classifier. The `1.0.0` availability state is `local_reference_runtime_available`.

## Workflow

1. Confirm whether the input is a local fixture, official sandbox/test key, self-owned system, authorized target, or unknown external target.
2. Inspect only the supplied assets and allowed observation sources.
3. Derive provider candidates, challenge family, scripts, frames, site/action bindings, token fields, and endpoints only from the supplied evidence.
4. Separate widget/challenge, provider verification, risk/session state, and final first-party business API stages.
5. Label every claim and list missing evidence.
6. Return the output contract below.

## Output contract

- provider candidates with confidence and evidence references
- challenge family and required solver capability
- script/frame/site binding inventory
- observed endpoints grouped by stage
- answer-shaped field leakage warnings
- fact claims and unresolved evidence
- authorization decision and allowed next step

## Boundaries

Official test keys and demos provide boundary evidence, not production capability. Unknown external targets remain observation-only. Do not use answer-shaped DOM, query, metadata, or server-expected fields as solver input.

## References

- [Provider observation contract](references/provider-observation-contract.md)
- [Leakage and test-key boundaries](references/leakage-and-test-key-boundaries.md)
