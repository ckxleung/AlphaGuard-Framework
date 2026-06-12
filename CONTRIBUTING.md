# Contributing

## Branches

Use `feature/layer[1-4]-[module-code]` branches. Keep `main` releasable.

## Commits

Use Conventional Commits:

```text
<type>(<scope>): <short description>
```

Examples:

- `feat(valuation): implement analytical EV capital bridge`
- `fix(supplychain): correct ROP variance aggregation`
- `test(compliance): add beneficial ownership omission cases`

## Test-Driven Kernel Workflow

1. Add failing tests for the deterministic rule and boundary conditions.
2. Implement one complete auditor with no placeholder branches.
3. Run unit tests and `python3 -m src.repository_validator`.
4. Review numerical tolerances, input validation, and scorecard evidence.
5. Register the implementation path and set its manifest status to
   `IMPLEMENTED`.

Before implementation begins, the module must have a complete immutable entry
in `src/kernel_spec_catalog.py`. Preserve canonical module IDs and codes when
incorporating external benchmark documents; record source aliases instead of
renumbering an established module.

Financial-statement kernels must document their sign convention, source ID,
fiscal period, units or currency, and numerical tolerance. Do not place live
network calls or fabricated fallback values inside deterministic kernels.

M&A valuation kernels must also document the valuation date, transaction or
market equity-value basis, every included debt-like and non-operating
adjustment, and whether the bridge represents announced, unaffected, or
closing-date terms.

## Required Pull Request Evidence

- deterministic ground-truth equation or regulatory source;
- accepted input schema;
- tolerance and rejection thresholds;
- unit, integration, and adversarial fixtures;
- proof that `execute_audit()` returns a valid institutional scorecard.

For publication-related changes, also provide:

- the approved document type and template;
- timezone-aware as-of and generated-at timestamps;
- claim classification and source references;
- methodology references for every material claim;
- a JSON sidecar that passes `src/output_standard.py`;
- confirmation that synthetic data and strategy risk are disclosed.

Temporal changes must include deterministic tests with injected UTC datetimes.
Do not test against the machine's current wall clock. DST transitions, market
session boundaries, and the holiday-calendar limitation must remain explicit.
