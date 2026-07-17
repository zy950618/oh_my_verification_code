# Output Quality Scorecard

Release: `1.0.0-rc.1`

| Gate | Status | Evidence |
|---|---|---|
| Canonical Skill names and boundaries | implemented | Six English Skills under `plugin/skills/` with contract-only RC availability metadata |
| Agent Skills frontmatter | observed | Six package structure and synchronized RC-boundary tests pass |
| Claude Code plugin validation | observed | `claude plugin validate ./plugin --strict` passed |
| Canonical contract schemas | observed | v1 contract schemas generated with Pydantic 2 match committed files byte-for-byte |
| Route and output evals | partial | Baseline route fixtures are structural inputs; package tests validate their declared RC boundaries but no routing harness executes them |
| Package clean install | observed | Editable install, wheel/sdist build, clean wheel install, core import, and blocked-command smoke passed |
| Success-semantics matrix | partial | Authorization, HTTP 200, repeat, ledger, prediction, action, replay-failure, and lineage-boundary tests pass with warnings treated as errors |
| Local first-party E2E | missing evidence | Reference lab exists; new receipt flow has not driven the lab process end-to-end |
| FastAPI/MCP transport surface | partial | Transport-scoped health, three fail-closed FastAPI routes, and two read-only MCP tools were observed; operational implementations remain missing evidence |
| Historical evidence preservation | observed | Legacy Skill tree archived; additive locator paths and content hashes validate without rewriting origin provenance |

This release candidate must not be described as provider-verified or production-ready until every required gate has observed evidence.
