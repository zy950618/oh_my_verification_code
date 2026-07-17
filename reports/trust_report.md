# Trust report

Release: `1.0.0-rc.1`

## Boundary

The public release has two artifacts: the Claude plugin contains provider-neutral Skills and their governance assets, while the Python distribution contains contracts, source, schemas, CLI, and adapter templates. Partner-specific target adapters, credentials, raw captures, browser profiles, and model weights are outside both artifacts.

## Dependencies

Core runtime dependencies are Pydantic and PyYAML. FastAPI, MCP, Playwright, Pillow, and training dependencies are optional extras.

## Browser tooling

CloakBrowser is not integrated. `js-reverse-mcp` is not a dependency. The first browser adapter, when enabled, uses an ordinary isolated Playwright context and cannot create a business-acceptance receipt.

## Authorization

A claimed or oral authorization remains `unverified`. Production execution requires a separately verified authorization record and scope. Target adapters cannot broaden their own scope.

## Evidence

Historical evidence is retained. Locator migration is additive and does not overwrite origin paths. Unique evidence is not deleted during this release.

## Observed release gates

- Canonical schemas match the committed `plugin/schemas/v1/` files byte-for-byte.
- The wheel and source distribution build; a clean wheel install imports the core and preserves blocked solver commands.
- `claude plugin validate ./plugin --strict` passes.
- Migration locators resolve to existing files with matching SHA-256 content hashes.
- Replay failure evidence, process status, and lineage split/audit boundaries have regression coverage.

## Missing evidence

- Independent live-provider benchmarks
- External authorization approval telemetry
- Complete local first-party receipt-chain E2E through the reference risk lab
- Implemented classify/solve/plan services behind the fail-closed transport stubs
