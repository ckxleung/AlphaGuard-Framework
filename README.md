# AlphaGuard Framework

AlphaGuard is a deterministic evaluation framework for auditing AI-generated
financial, compliance, telemetry, and strategy artifacts.

## Current Repository State

This repository contains the engineering contract required before individual
evaluation kernels are implemented:

- one abstract `BaseAuditor.execute_audit()` interface;
- a fail-closed institutional scorecard schema;
- four required kernel layers;
- an immutable registry covering module IDs 1 through 18;
- placeholder and structure validation;
- a one-command pipeline entry point.

The supplied source specification defines 17 unique module codes. Module 12 was
not supplied and is deliberately marked `SPEC_REQUIRED`. No fabricated business
logic is treated as production-ready.

## Required Structure

```text
evaluation_kernels/
  layer_1_telemetry/
  layer_2_valuation/
  layer_3_compliance/
  layer_4_strategy/
src/
  base_auditor.py
  main_pipeline.py
  module_manifest.py
  repository_validator.py
tests/
```

## Quick Start

```bash
python3 -m unittest discover -s tests -p "test_*.py"
python3 -m src.repository_validator
python3 -m src.main_pipeline --validate-only
```

## Kernel Contract

Every production kernel must:

1. live under its assigned layer;
2. define the class registered in `src/module_manifest.py`;
3. inherit from `BaseAuditor`;
4. implement `execute_audit(ai_output, ground_truth)`;
5. return a scorecard containing `rigor_score`, `data_quality_status`, and
   `structured_written_feedback`;
6. contain no placeholder implementation;
7. be accompanied by deterministic unit, integration, and boundary tests.

## Delivery Rule

A module may be changed from `SPECIFIED` to `IMPLEMENTED` only after its input
schema, deterministic equation or regulatory rule, tolerance policy, fixtures,
and implementation path have all been reviewed and tested.
