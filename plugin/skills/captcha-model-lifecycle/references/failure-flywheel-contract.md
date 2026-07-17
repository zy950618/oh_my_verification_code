# Failure flywheel contract

A failure record preserves the original input hash, solver/model versions, prediction, expected value held by the evaluator, error class, evidence references, authorization scope, and replay result.

A source-run selector must actually filter the collected failures. Replayed failures remain linked to their original challenge lineage and may not silently change label source or acquisition mode.
