---
name: captcha-solver-core
description: Define and validate provider-neutral prediction contracts and solver registry decisions for local or authorized CAPTCHA assets. Includes a raster-only local fixture classifier and slider/rotate/click reference solvers; it does not perform browser execution or claim third-party business acceptance.
when_to_use: Use when a normalized prediction contract, solver registry decision, leakage gate, or missing-implementation report is needed.
license: MIT
compatibility: Requires Python 3.11+ and the captcha-verification-skills package. The optional vision extra is a dependency hook and does not add a bundled solver.
argument-hint: "[challenge asset path]"
metadata:
  owner: zhaoyang
  version: "1.0.0"
  lifecycle: library
---

# CAPTCHA Solver Core

Define and validate normalized prediction contracts for approved input assets. A prediction is not provider or business acceptance.

## Release candidate boundary

Defines and validates prediction contracts and registry decisions, and documents the bundled raster-only local fixture classifier plus slider/rotate/click reference solvers. The `1.0.0` availability state is `local_reference_runtime_available`; external targets remain unsupported.

## Workflow

1. Validate asset types, hashes, size, coordinate frame, and authorization context.
2. Classify provider candidates and challenge family when needed.
3. Inspect the versioned solver registry for a compatible externally supplied implementation.
4. Build a raster-only solver input. Strip SVG/XML/DOM/data/ARIA metadata before inference.
5. If no external implementation is registered, return blocked with missing implementation evidence. Otherwise validate its prediction envelope; this RC does not run a bundled solver.
6. Evaluate ground truth in a separate process that the solver cannot read.

## Output contract

- `prediction_status`: `produced`, `low_confidence`, `unsupported`, or `failed`
- normalized solution fields: `text`, `points`, `tiles`, `offset`, `angle_degrees`, `track`, `press`
- solver/model/dataset/preprocessing versions and hashes
- confidence and calibration version
- input and output evidence references
- fact claims and `business_acceptance_status: not_attempted`

## Boundaries

Expected answers, labels, evaluator thresholds, DOM metadata, and server-side answers are forbidden solver inputs. Empty or unsupported predictions cannot be marked produced. Solver metrics may promote only a scoped solver benchmark capability.

## References

- [Normalized solution contract](references/normalized-solution-contract.md)
- [Raster-only and leakage gate](references/raster-only-and-leakage-gate.md)
- [Solver registry contract](references/solver-registry-contract.md)
