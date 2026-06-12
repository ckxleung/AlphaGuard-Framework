# AlphaGuard Codex Contract

## Repository

- Target: `https://github.com/ckxleung/AlphaGuard-Framework.git`
- Runtime: Python 3.10+
- Production branch: `main`
- Feature branches: `feature/layer[1-4]-[module-code]`

## Required Kernel Locations

- Layer 1: `evaluation_kernels/layer_1_telemetry/`
- Layer 2: `evaluation_kernels/layer_2_valuation/`
- Layer 3: `evaluation_kernels/layer_3_compliance/`
- Layer 4: `evaluation_kernels/layer_4_strategy/`

## Mandatory Auditor Interface

Every production kernel must:

1. inherit from `src.base_auditor.BaseAuditor`;
2. implement `execute_audit(ai_output, ground_truth)`;
3. validate all external inputs before calculation;
4. use deterministic domain logic for ground truth;
5. return a scorecard accepted by `BaseAuditor.validate_scorecard`;
6. avoid mutation of caller-owned inputs;
7. contain no placeholder branches, empty functions, or unfinished markers.

## Scorecard Contract

Every result must contain:

- `rigor_score`: finite number from `0.0` through `5.0`;
- `data_quality_status`: `APPROVED` or `REJECTED`;
- `structured_written_feedback`: non-empty institutional feedback.

Evidence fields may be added, but required fields cannot be renamed.

## Development Workflow

1. Work on one module at a time.
2. Write failing tests before implementation.
3. Cover deterministic equations, parser boundaries, tolerance limits, and
   adversarial cases.
4. Implement the complete module without placeholder logic.
5. Register its exact class and path in `src/module_manifest.py`.
6. Change status to `IMPLEMENTED` only after tests and validation pass.
7. Run:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
python3 -m src.repository_validator
python3 -m src.main_pipeline --validate-only
```

## Specification Safety

- Never invent missing financial equations, regulatory obligations, tolerance
  ceilings, company routes, or fixtures.
- Module 12 remains `SPEC_REQUIRED` until an approved specification is supplied.
- The source brief duplicated Module 07; do not treat that duplication as an
  eighteenth unique module.
- A module description is not sufficient for production status. Require input
  schema, deterministic rule, tolerance policy, and test fixtures.

## Git

Use Conventional Commits:

```text
<type>(<scope>): <short description>
```

Never push directly to `main` without passing the complete validation suite.
