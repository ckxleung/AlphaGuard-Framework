# AlphaGuard Framework

AlphaGuard is a deterministic evaluation framework for auditing AI-generated
financial, compliance, telemetry, and strategy artifacts.

## Current Repository State

This repository contains the engineering contract required before individual
evaluation kernels are implemented:

- one abstract `BaseAuditor.execute_audit()` interface;
- a fail-closed institutional scorecard schema;
- four required kernel layers;
- an external 55-enterprise telemetry configuration;
- an immutable registry covering module IDs 1 through 18;
- a daily GitHub Actions telemetry workflow at 04:00 HKT;
- placeholder and structure validation;
- a one-command pipeline entry point.

The repaired source specification now defines all 18 unique module codes.
IRTA, BMAE, and SCGV are implemented and registered; the remaining 15 modules
remain explicitly `SPECIFIED` until their complete schemas, tolerance policies,
and adversarial fixtures are implemented.

## Required Structure

```text
evaluation_kernels/
  layer_1_telemetry/
    Module_05_SFRA/
    Module_06_TLAB/
    Module_10_OAPE/
  layer_2_valuation/
    Module_02_APAC/
    Module_09_FITV/
    Module_11_CVIB/
    Module_14_CFIA/
    Module_18_IBDV/
  layer_3_compliance/
    Module_01_FRTE/
    Module_08_FOAS/
    Module_16_AMWE/
    Module_17_ERCA/
  layer_4_strategy/
    Module_03_AMDG/
    Module_04_CASS/
    Module_07_BLSB/
    Module_12_IRTA/
    Module_13_BMAE/
    Module_15_SCGV/
config/
  target_55_enterprises.json
src/
  base_auditor.py
  main_pipeline.py
  module_manifest.py
  repository_validator.py
  telemetry_router.py
tests/
docs/
.github/workflows/
  ci.yml
  daily_telemetry_cron.yml
```

## Quick Start

```bash
python3 -m unittest discover -s tests -p "test_*.py"
python3 -m src.repository_validator
python3 -m src.main_pipeline --validate-only
python3 src/main_pipeline.py
```

Coverage verification:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m coverage run --source=src,evaluation_kernels -m unittest discover -s tests
python3 -m coverage report --fail-under=80
```

The canonical formulas and rejection contracts are documented in
[`docs/MASTER_SPEC.md`](docs/MASTER_SPEC.md).

## Daily Telemetry Loop

The scheduled workflow in `.github/workflows/daily_telemetry_cron.yml` runs
`python src/main_pipeline.py` every day at 04:00 HKT. The router reads
`config/target_55_enterprises.json`, maps each covered ticker into its assigned
defense layer, and preserves explicit high-priority routes for critical names
such as NVDA and AVGO.

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
