# Generated adapter test matrix

A generated package must pass:

- manifest and schema validation;
- deterministic regeneration and content hashes;
- import and protocol conformance;
- all methods fail closed before implementation;
- authorization missing, expired, host mismatch, and action mismatch tests;
- test-key/provider-only acceptance does not become business acceptance;
- no driver or network call during generation;
- path traversal and public-partner-output rejection;
- secret, raw capture, browser profile, and model-weight exclusion.
