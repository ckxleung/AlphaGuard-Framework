# AlphaGuard Kernel Implementation Roadmap

## Purpose

This roadmap converts the eighteen-kernel architecture from a specification
inventory into an executable build plan. It is intentionally conservative:
`IMPLEMENTED` means a kernel has executable code, inherits from
`BaseAuditor`, is registered in `src/module_manifest.py`, and has deterministic
tests. `SPECIFIED` means the module has a complete machine-readable contract in
`src/kernel_spec_catalog.py`, but its production auditor has not been promoted.

The roadmap is part of the repository contract. Tests assert that every
canonical module appears here with the same status as the immutable manifest.

## Current Production Baseline

- Monitored universe: 56 tickers in `config/target_enterprises.json`.
- Architecture coverage: 18 canonical modules across four functional layers.
- Production auditors live: 8.
- Specified auditors awaiting implementation: 10.
- Shared runtime contract: `BaseAuditor.execute_audit(ai_output, ground_truth)`.
- Publication contract: Markdown report plus JSON sidecar validated by
  `src/output_standard.py`.

## Implementation Matrix

| ID | Code | Layer | Status | Build Wave | Promotion Gate |
|---:|---|---|---|---|---|
| 01 | FRTE | layer_3_compliance | SPECIFIED | Wave 3 | QoQ filing delta fixtures with source-span evidence |
| 02 | APAC | layer_2_valuation | SPECIFIED | Wave 4 | Timestamped options-skew and regulatory-contagion fixtures |
| 03 | AMDG | layer_4_strategy | SPECIFIED | Wave 4 | Render-inspection fixtures for institutional deliverables |
| 04 | CASS | layer_4_strategy | SPECIFIED | Wave 5 | Persona constraint matrix and conflict-resolution fixtures |
| 05 | SFRA | layer_1_telemetry | SPECIFIED | Wave 2 | SEC footnote retrieval fixtures with coordinate citations |
| 06 | TLAB | layer_1_telemetry | SPECIFIED | Wave 2 | Versioned API schema and execution-trace fixtures |
| 07 | BLSB | layer_4_strategy | SPECIFIED | Wave 5 | Strategy claim-evidence mapping and actionability fixtures |
| 08 | FOAS | layer_3_compliance | IMPLEMENTED | Live | Cent-level ledger, trial-balance, adjustment traceability, and CLI tests passed |
| 09 | FITV | layer_2_valuation | IMPLEMENTED | Live | Bond price, duration, DV01, convention, and CLI tests passed |
| 10 | OAPE | layer_1_telemetry | SPECIFIED | Wave 3 | Office package and rendered-layout pairwise fixtures |
| 11 | CVIB | layer_2_valuation | IMPLEMENTED | Live | DCF, WACC, terminal-value, per-share, multiple, convention, and CLI tests passed |
| 12 | IRTA | layer_4_strategy | IMPLEMENTED | Live | Capacity-ceiling and CAGR boundary tests passed |
| 13 | BMAE | layer_4_strategy | IMPLEMENTED | Live | Market-microstructure noise-filter tests passed |
| 14 | CFIA | layer_2_valuation | IMPLEMENTED | Live | Operating-cash-flow reconciliation tests passed |
| 15 | SCGV | layer_4_strategy | IMPLEMENTED | Live | Safety-stock and reorder-point stochastic tests passed |
| 16 | AMWE | layer_3_compliance | SPECIFIED | Wave 3 | Time-series leakage and split-integrity fixtures |
| 17 | ERCA | layer_3_compliance | SPECIFIED | Wave 4 | COSO-style control matrix and evidence-inventory fixtures |
| 18 | IBDV | layer_2_valuation | IMPLEMENTED | Live | Enterprise-value capital-bridge tests passed |

## Recommended Build Sequence

### Wave 1: Valuation Demonstration Depth

Wave 1 is now complete. Implemented `CVIB`, `FITV`, `CFIA`, and `IBDV` form the
first high-value valuation demonstration lane:

- `Module_09_FITV`: implemented fixed-income price, modified duration, and
  DV01 checks;
- `Module_11_CVIB`: implemented DCF, terminal value, WACC, per-share value, and
  comparable-company multiple checks.

This wave is the most useful for buy-side, banking, and independent-research
readers because it produces deterministic finance math that is easy to inspect.

### Wave 2: Daily Infrastructure Credibility

`FOAS` is now implemented. Promote `TLAB` and `SFRA` next to add API-contract
checking and long-context filing evidence to the daily telemetry loop:

- `Module_08_FOAS`: implemented ledger, trial-balance, and adjustment
  reconciliation;
- `Module_06_TLAB`: API schema, generated-code, and tool-trace validation;
- `Module_05_SFRA`: SEC footnote retrieval and citation integrity.

Wave 2 turns AlphaGuard from a valuation demo into a daily operating system for
auditable AI output.

### Wave 3: Forensic Evidence Expansion

Promote `FRTE`, `OAPE`, and `AMWE` once ingestion fixtures exist:

- `Module_01_FRTE`: filing risk-delta omissions and invented changes;
- `Module_10_OAPE`: office artifact structural and rendered-layout defects;
- `Module_16_AMWE`: temporal leakage and invalid model-validation splits.

### Wave 4: Enterprise and Cross-Market Controls

Promote `APAC`, `AMDG`, and `ERCA` after the framework has stable evidence
adapters:

- `Module_02_APAC`: cross-market operating, options, and regulatory contagion;
- `Module_03_AMDG`: institutional deliverable numerical and visual discipline;
- `Module_17_ERCA`: enterprise risk and compliance control coverage.

### Wave 5: Strategy Sandbox Completion

Promote `CASS` and `BLSB` last because they require richer qualitative fixtures
and higher reviewer judgment:

- `Module_04_CASS`: stakeholder-conflict strategy resolution;
- `Module_07_BLSB`: GTM strategy grounding, actionability, and downside control.

## Promotion Checklist

A module can move from `SPECIFIED` to `IMPLEMENTED` only when all items pass:

1. implementation lives under the assigned layer and module directory;
2. class name matches `src/module_manifest.py`;
3. class inherits from `BaseAuditor`;
4. `execute_audit(ai_output, ground_truth)` validates inputs and fails closed;
5. deterministic equation, rule, or regulatory check is implemented directly;
6. tolerance policy is explicit and test-covered;
7. synthetic fixtures are labeled and source IDs are required;
8. unit tests cover approved, rejected, boundary, malformed, and immutability
   cases;
9. standalone CLI execution works outside the repository root;
10. `python3 -m src.repository_validator` passes.

## Current High-Value Production Example

`Module_18_IBDV` is the current banking-grade reference implementation. It
audits an equity-value-to-enterprise-value bridge:

```text
enterprise value =
  equity value
  + total debt
  - cash and equivalents
  + preferred stock
  + non-controlling interests
```

It rejects internally inconsistent ground truth before judging the AI output,
then detects missing bridge components such as preferred stock and
non-controlling interests. This is the standard expected of future valuation
modules: deterministic formula, source provenance, declared tolerance, and
explicit scorecard evidence.
