# Solver registry contract

A solver registry entry contains:

- stable ID and semantic version;
- import path and callable;
- input and output schema versions;
- supported challenge families and solution types;
- optional model and dataset bindings;
- latency class and concurrency-safety declaration;
- lifecycle state and deprecation replacement;
- package and artifact checksums;
- health and smoke-test results.

Registry validation imports the callable and runs a fixture. A string label alone is not a valid registry entry.
