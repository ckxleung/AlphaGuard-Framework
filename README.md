# AlphaGuard Framework

AlphaGuard is a deterministic evaluation framework for auditing AI-generated
financial, compliance, telemetry, and strategy artifacts.

Supported runtime: Python 3.10 through 3.13. Python 3.14 is not currently
supported because the secured LiteLLM dependency line declares `<3.14`.

## Current Repository State

This repository contains the engineering contract required before individual
evaluation kernels are implemented:

- one abstract `BaseAuditor.execute_audit()` interface;
- a fail-closed institutional scorecard schema;
- four required kernel layers;
- an external 56-enterprise telemetry configuration;
- an immutable registry covering module IDs 1 through 18;
- a machine-readable specification catalog covering every module's inputs,
  deterministic rules, tolerance policy, rejection conditions, outputs, and
  data boundary;
- a cohort and event-driven monitoring control plane for the monitored enterprise
  universe;
- a daily GitHub Actions telemetry workflow at 04:00 HKT;
- a DST-aware three-market timestamp matrix;
- a machine-verifiable institutional publication contract;
- a SHA-256-backed source-document registry with exact citation locators;
- placeholder and structure validation;
- a one-command pipeline entry point.

The repaired source specification now defines all 18 unique module codes.
FITV, IRTA, BMAE, CFIA, SCGV, and IBDV are implemented and registered; the
remaining 12 modules have complete specification contracts but remain explicitly
`SPECIFIED` until their executable auditors and adversarial fixtures are
implemented.

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
  enterprise_monitoring_profiles.json
  event_routing_policy.json
  source_registry.json
  target_enterprises.json
schemas/
  publication_artifact.schema.json
  source_registry.schema.json
templates/
  telemetry_note.md
  deep_dive_whitepaper.md
src/
  base_auditor.py
  kernel_spec_catalog.py
  main_pipeline.py
  market_clock.py
  monitoring_control_plane.py
  module_manifest.py
  output_standard.py
  repository_validator.py
  source_registry.py
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
python3 src/monitoring_control_plane.py --event examples/monitoring_event.example.json
python3 src/monitoring_control_plane.py --event examples/monitoring_event.rate_shock.synthetic.json --module-payloads examples/module_payloads.rate_shock.synthetic.json
python3 src/monitoring_control_plane.py --portfolio-baseline
python3 src/output_standard.py examples/publication_artifact.example.json
python3 src/source_registry.py config/source_registry.json
```

Coverage verification:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m coverage run --source=src,evaluation_kernels -m unittest discover -s tests
python3 -m coverage report --fail-under=80
```

The canonical formulas and rejection contracts are documented in
[`docs/MASTER_SPEC.md`](docs/MASTER_SPEC.md).
The corresponding CI-verifiable records live in
[`src/kernel_spec_catalog.py`](src/kernel_spec_catalog.py).
The implementation order and promotion gates are tracked in
[`docs/KERNEL_IMPLEMENTATION_ROADMAP.md`](docs/KERNEL_IMPLEMENTATION_ROADMAP.md).

Implemented accounting kernels consume explicit, source-identified inputs.
They do not download market data, substitute fabricated fallback values, or
silently convert missing fields to zero. External ingestion adapters must
normalize and provenance financial statements before invoking a kernel.

## Daily Telemetry Loop

The scheduled workflow in `.github/workflows/daily_telemetry_cron.yml` runs
every day at 04:00 HKT. It validates the repository, generates a planning-only
56-enterprise baseline artifact, and runs the deterministic synthetic smoke test.
The plan never claims that live collection or an audit occurred.

The monitoring control plane combines three business cohorts with the four
functional infrastructure layers. Daily baseline routes exactly two modules;
event-driven peaks route between three and five. Selected but unimplemented
kernels remain visible as `unavailable_modules`, while implemented kernels
without evidence payloads are reported as skipped. See
[`docs/MONITORING_OPERATIONS.md`](docs/MONITORING_OPERATIONS.md).

The target universe currently contains 56 monitored tickers.

## Institutional Output Contract

AlphaGuard publication is a two-file contract:

1. a human-readable Markdown report created from an approved template;
2. a machine-readable JSON sidecar containing claims, sources, timestamps,
   scorecards, and disclosures.

The canonical editorial and evidence standard is documented in
[`docs/OUTPUT_STANDARD.md`](docs/OUTPUT_STANDARD.md). The machine schema lives
in
[`schemas/publication_artifact.schema.json`](schemas/publication_artifact.schema.json).
Examples containing synthetic data are explicitly labeled and must pass
`src/output_standard.py` before publication.

Source documents are registered separately from report citations. The registry
stores stable document IDs, issuer metadata, retrieval timestamps, SHA-256
snapshot hashes, and primary-source classification. Each report citation adds
an exact page, section, table, exhibit, paragraph, cell, timestamp, line, or
JSON-pointer locator. See
[`docs/SOURCE_REGISTRY.md`](docs/SOURCE_REGISTRY.md).

## Cross-Market Time Integrity

Every smoke run and publication artifact carries a synchronized UTC, New York,
Hong Kong, and Shanghai timestamp matrix. New York EST/EDT conversion is
handled by the standard-library `zoneinfo` database. Scheduled market states
include pre-market, regular tape, lunch breaks, closing auctions, post-market,
and weekend closure.

The current engine intentionally declares
`calendar_basis: WEEKDAY_SCHEDULE_ONLY`; exchange holidays and extraordinary
closures are not presented as resolved. See
[`docs/TEMPORAL_STANDARD.md`](docs/TEMPORAL_STANDARD.md).

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

`SPECIFIED` means the module has a complete entry in
`src/kernel_spec_catalog.py`; it does not mean executable kernel code exists.

The next recommended build target is `CVIB`, which completes Wave 1 around live
`FITV`, `CFIA`, and `IBDV` valuation auditors.

## Open-Core Security Boundary

AlphaGuard contains no production API credentials, licensed feeds, or
confidential institutional datasets. Live connectors must be supplied
separately with explicit provenance and secret management. This repository does
not claim that undisclosed private-cloud infrastructure is already deployed.
