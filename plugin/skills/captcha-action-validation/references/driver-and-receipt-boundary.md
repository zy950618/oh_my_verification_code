# Driver and receipt boundary

A driver receives an already validated authorization record and action plan. It may produce observation and execution receipts containing actual events and evidence artifacts.

A driver cannot:

- expand authorization scope;
- create a business-acceptance receipt;
- promote a capability;
- enable stealth, fingerprint spoofing, clearance reuse, or token fabrication through this core contract.

The first reference adapter uses ordinary isolated Playwright contexts. CloakBrowser is not integrated. `js-reverse-mcp` is not a dependency.
