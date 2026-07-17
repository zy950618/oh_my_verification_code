# Provider observation contract

A provider observation records candidates rather than forcing a single provider when evidence is ambiguous. Each candidate includes markers, confidence, evidence references, and a fact level.

Group observed endpoints into:

1. widget or challenge configuration;
2. provider verification;
3. session or risk state;
4. final protected first-party business API.

Observation must record asset freshness and hashes. A response status or provider `success` field is not a final business decision.
