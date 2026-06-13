# Monitoring Operations

## Operating Model

AlphaGuard separates four responsibilities:

1. **Ingestion adapters** capture public evidence with provenance.
2. **Monitoring control plane** maps each target and event to two daily or
   three-to-five event-driven kernels.
3. **Evaluation kernels** execute deterministic audits using module-specific
   payloads.
4. **Publication contract** decides whether a report has sufficient evidence
   and disclosures for external release.

The public repository implements the control plane and five executable kernels.
It does not claim that live source connectors, proprietary datasets, or the
remaining thirteen kernels exist.

## Cohorts

The 56 monitored tickers are assigned exactly once in
`config/enterprise_monitoring_profiles.json`:

- `FOUNDATIONAL_API`
- `ENTERPRISE_FINTECH_AGENT`
- `COMPUTE_INFRASTRUCTURE`

These are business monitoring cohorts, not replacements for the four
functional infrastructure layers. Each loaded profile is reconciled to
`config/target_enterprises.json` and therefore also carries one functional
defense layer:

- `Layer_1_Technical_Telemetry`;
- `Layer_2_Quantitative_Valuation`;
- `Layer_3_Regulatory_Compliance`;
- `Layer_4_Institutional_Strategy`.

The cohort decides editorial priority and likely event types. The functional
layer decides the default infrastructure lane and makes the 18-kernel
architecture visible in every plan.

The profile universe must exactly match `config/target_enterprises.json`.
Each cohort also declares preferred event types. The control plane labels an
event as `PREFERRED`, `SECONDARY`, or `BASELINE` for alert and editorial
prioritization; it does not suppress valid secondary events.

## Routing Policy

`config/event_routing_policy.json` is the authoritative policy.

- Daily baseline selects exactly `TLAB` and `BMAE`.
- Event routes select between three and five modules.
- Selected but unimplemented modules are reported as `unavailable_modules`.
- Implemented modules without a validated payload are reported as
  `skipped_executable_modules`.

This prevents the system from generating fabricated scorecards merely to make
an event appear fully covered.

## Event Contract

```json
{
  "event_id": "unique-event-id",
  "ticker": "NVDA",
  "event_type": "FINANCING_MA",
  "observed_at": "2026-06-13T00:00:00Z",
  "evidence_refs": ["DOC-SEC-10Q-20260613-EXAMPLE"],
  "data_classification": "PUBLIC_SOURCE"
}
```

Supported classifications:

- `PLANNING_ONLY`: routing exercise without audit evidence;
- `SYNTHETIC`: deterministic development fixture;
- `PUBLIC_SOURCE`: candidate production evidence.

Every non-empty `evidence_refs` value must resolve to
`config/source_registry.json`. `PUBLIC_SOURCE` events cannot cite a document
registered as `INTERNAL_FIXTURE`. See
[`SOURCE_REGISTRY.md`](SOURCE_REGISTRY.md).

`PUBLIC_SOURCE` alone does not make a report publishable. All selected modules
must be implemented, supplied with validated payloads, and successfully
executed before `publication_eligible` can become true.

## Commands

Plan one event:

```bash
python3 src/monitoring_control_plane.py \
  --event examples/monitoring_event.example.json
```

Run the synthetic financing demonstration:

```bash
python3 src/monitoring_control_plane.py \
  --event examples/monitoring_event.example.json \
  --module-payloads examples/module_payloads.financing.synthetic.json
```

Run the synthetic fixed-income rate-shock demonstration:

```bash
python3 src/monitoring_control_plane.py \
  --event examples/monitoring_event.rate_shock.synthetic.json \
  --module-payloads examples/module_payloads.rate_shock.synthetic.json
```

Generate the daily 56-enterprise routing plan:

```bash
python3 src/monitoring_control_plane.py \
  --portfolio-baseline \
  --observed-at 2026-06-13T00:00:00Z
```

Run the event-aware synthetic smoke pipeline without live market ingestion:

```bash
python3 src/main_pipeline.py --ticker NVDA --event earnings_release
```

This command preserves event policy order, executes only implemented selected
kernels, and discloses unimplemented selected kernels in `unavailable_kernels`.

## Publication Gate

A monitoring run remains non-publishable when any of the following is true:

- selected modules are unimplemented;
- executable modules lack payloads;
- no source references are supplied;
- data is planning-only or synthetic;
- no scorecards are produced.

Publishable research must then be wrapped in the separate schema described in
`docs/OUTPUT_STANDARD.md`.

## Security and Open-Core Boundary

No API key, token, confidential dataset, or licensed feed belongs in this
repository. External connectors must obtain credentials from environment
variables or a secret manager and write raw snapshots only to ignored local or
controlled storage.

This repository is an open evaluation and telemetry core. It makes no claim
that private cloud connectors or undisclosed commercial infrastructure are
currently deployed.
