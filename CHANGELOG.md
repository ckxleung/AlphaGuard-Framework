# Changelog

All notable AlphaGuard Framework changes are recorded here. The project follows
human-readable milestone versions until public package releases begin.

## v0.7.0 - 2026-06-16

- Completed the full 18-kernel implementation baseline across telemetry,
  valuation, compliance, and strategy layers.
- Promoted `FRTE`, `APAC`, `AMDG`, `CASS`, `BLSB`, `OAPE`, `AMWE`, and `ERCA`
  to production auditors with deterministic tests and manifest registration.
- Updated the institutional gate expectation: downstream publication systems
  must fail closed when AlphaGuard repository validation, kernel execution, or
  machine-readable sidecar validation fails.
- Verified 188 unit and contract tests across all production auditors.

## v0.6.0 - 2026-06-14

- Added `Module_05_SFRA` as a production auditor.
- Introduced SEC filing footnote-boundary, table-cell, cross-reference graph,
  answer-value, source-coordinate, and position-bucket retrieval checks.
- Updated Layer 1 smoke coverage so foundational telemetry routes execute SFRA
  and TLAB while disclosing only unavailable OAPE.
- Raised the implementation baseline to 10 production auditors and 8 specified
  auditors awaiting promotion.

## v0.5.0 - 2026-06-14

- Added `Module_06_TLAB` as a production auditor.
- Introduced versioned API schema, generated Python code, auth header,
  rate-limit retry, error-handling, and chained execution-trace checks.
- Updated Layer 1 smoke coverage so foundational telemetry routes can execute
  TLAB while still disclosing unavailable SFRA and OAPE kernels.
- Raised the implementation baseline to 9 production auditors and 9 specified
  auditors awaiting promotion.

## v0.4.0 - 2026-06-14

- Added `Module_08_FOAS` as a production auditor.
- Introduced cent-level ledger, trial-balance, adjustment-balance, and source-row
  traceability checks using `Decimal` arithmetic.
- Updated Layer 3 smoke coverage so routine compliance routes can execute FOAS.
- Raised the implementation baseline to 8 production auditors and 10 specified
  auditors awaiting promotion.

## v0.3.0 - 2026-06-14

- Added `Module_11_CVIB` as a production auditor.
- Completed the Wave 1 valuation lane with DCF, terminal-value, per-share, and
  comparable-company multiple checks.
- Updated financing and rate-shock examples to execute CVIB.

## v0.2.0 - 2026-06-13

- Added source registry and exact citation locator requirements.
- Added publication artifact validation and synthetic monitoring examples.
- Added event-driven control-plane disclosure for unavailable and skipped
  kernels.

## v0.1.0 - 2026-06-12

- Established the 18-kernel architecture across four functional layers.
- Added the shared `BaseAuditor` scorecard contract.
- Added telemetry router, daily smoke pipeline, enterprise universe, and initial
  production auditors.
