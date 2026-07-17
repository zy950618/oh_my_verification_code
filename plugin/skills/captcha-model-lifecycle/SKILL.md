---
name: captcha-model-lifecycle
description: Audit CAPTCHA dataset and model-lifecycle contracts, provenance, grouped splits, leakage evidence, evaluations, and promotion decisions. This release candidate does not bundle training, packaging, replay, or active-learning runtimes.
when_to_use: Use when auditing supplied dataset, training, benchmark, failure, or model-package evidence and deciding whether scoped registry promotion is blocked.
license: MIT
compatibility: Requires Python 3.11+ and the captcha-verification-skills package. Training and vision extras are dependency hooks and do not add bundled lifecycle services.
argument-hint: "[dataset, model package, or run ID]"
metadata:
  owner: zhaoyang
  version: "1.0.0-rc.1"
  lifecycle: library
---

# CAPTCHA Model Lifecycle

Audit reproducible data and model lifecycle contracts without confusing model metrics with action or business success.

## Release candidate boundary

Audits lifecycle contracts and evidence; no training or model-lifecycle runtime is bundled. The `1.0.0-rc.1` availability state is `blocked_without_external_implementation`.

## Workflow

1. Validate acquisition scope, provenance, licensing, synthetic/manual/automatic label source, and redaction.
2. Group samples by challenge lineage, template, source image, session, provider flow, and acquisition batch before splitting.
3. Audit exact content hashes, perceptual near-duplicates, template hashes, and lineage across splits.
4. Validate that supplied training evidence pins code, configuration, dataset/split hashes, and deterministic seeds where supported.
5. Audit supplied evaluations for holdout families, negative controls, calibration, latency, and failure distributions.
6. Run raster-only, black-box, leakage, model-load, and inference smoke gates.
7. Return a lifecycle decision and missing implementation evidence; packaging or registration requires an external implementation and all scoped gates.
8. Preserve failures and evidence references for replay.

## Output contract

- dataset/model/run identity and schema versions
- provenance, split, leakage, and license decisions
- metrics by family and difficulty
- artifact hashes and load/inference smoke results
- registry and promotion decisions with missing evidence
- failure sample references and next lifecycle action

## Boundaries

Synthetic data must be labeled synthetic. Automatically generated labels must not be called manual. Aggregate metrics cannot hide failed families. A trained or registered model does not imply provider verification, action success, or business acceptance.

## References

- [Dataset provenance and split contract](references/dataset-provenance-and-split-contract.md)
- [Model promotion contract](references/model-promotion-contract.md)
- [Failure flywheel contract](references/failure-flywheel-contract.md)
