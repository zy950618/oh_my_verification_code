# Target adapter boundary

Public Skills and the provider-neutral core do not contain partner-specific targets. A target adapter belongs in a private overlay and must include a versioned target manifest, authorization record, capability manifest, acceptance assertions, contract tests, and negative controls.

Generating an adapter is not executing it. The generator must not navigate, start a browser, call a target, load a private credential, or claim target compatibility.

A driver can create observation or execution receipts. It cannot create a first-party business-acceptance receipt or promote a capability.
