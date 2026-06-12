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

## Required Pull Request Evidence

- deterministic ground-truth equation or regulatory source;
- accepted input schema;
- tolerance and rejection thresholds;
- unit, integration, and adversarial fixtures;
- proof that `execute_audit()` returns a valid institutional scorecard.
