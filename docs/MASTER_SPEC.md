# AlphaGuard Master Specification

## Canonical Module Matrix

The registry contains exactly eighteen unique module IDs. Module 13 and Module
15 existed in the original matrix; the repaired specification below completes
their input/output and deterministic rejection contracts. Module 12 IRTA fills
the previously missing unique ID.

| ID | Code | Layer | Status |
|---:|---|---|---|
| 01 | FRTE | Layer 3 Compliance | Specified |
| 02 | APAC | Layer 2 Valuation | Specified |
| 03 | AMDG | Layer 4 Strategy | Specified |
| 04 | CASS | Layer 4 Strategy | Specified |
| 05 | SFRA | Layer 1 Telemetry | Specified |
| 06 | TLAB | Layer 1 Telemetry | Specified |
| 07 | BLSB | Layer 4 Strategy | Specified |
| 08 | FOAS | Layer 3 Compliance | Specified |
| 09 | FITV | Layer 2 Valuation | Specified |
| 10 | OAPE | Layer 1 Telemetry | Specified |
| 11 | CVIB | Layer 2 Valuation | Specified |
| 12 | IRTA | Layer 4 Strategy | Implemented |
| 13 | BMAE | Layer 4 Strategy | Implemented |
| 14 | CFIA | Layer 2 Valuation | Implemented |
| 15 | SCGV | Layer 4 Strategy | Implemented |
| 16 | AMWE | Layer 3 Compliance | Specified |
| 17 | ERCA | Layer 3 Compliance | Specified |
| 18 | IBDV | Layer 2 Valuation | Specified |

## Module 12 IRTA

**Name:** Buy-Side Institutional Research Thesis Auditor

**Purpose:** Prevent unsupported nonlinear revenue forecasts in AI-generated
investment theses.

### Deterministic Equation

For each forecast year `t`:

```text
available_capacity[t]
  = current_capacity
  + cumulative_capex_additions[t] * capital_efficiency

revenue_ceiling[t]
  = available_capacity[t] * max_utilization * blended_asp

expected_revenue[t] <= revenue_ceiling[t]
```

### Required Inputs

AI output:

- `revenue_forecast`: exactly five non-negative annual revenue values;
- `investment_thesis`: optional narrative evidence.

Ground truth:

- `current_capacity`;
- `capex_additions`: exactly five annual additions;
- `capital_efficiency`;
- `max_utilization`, greater than zero and no greater than one;
- `blended_asp`.

### Rejection Rule

Any annual breach rejects the artifact and applies a fixed three-point penalty
to the five-point rigor score. The scorecard reports breached years, annual
ceilings, implied utilization, and forecast CAGR.

## Module 13 BMAE

**Name:** Behavioral Market-Microstructure Alpha Engine

**Purpose:** Distinguish retail discussion noise from institutionally confirmed
flow and price signals.

### Deterministic Equation

```text
flow_ratio[t]
  = block_trades_outflow[t] / retail_orderflow_imbalance[t]

signal_purity_coefficient
  = covariance(sentiment_change, flow_ratio)
```

The implementation also calculates:

```text
noise_inflation_ratio
  = latest_discussion_volume / median_prior_discussion_volume

signal_to_noise_db
  = 10 * log10(price_signal_power / sentiment_price_residual_power)
```

### Required Inputs

AI output:

- `sentiment_changes`;
- `rating`.

Ground truth:

- `block_trades_outflow`;
- `retail_orderflow_imbalance`, with no zero denominator;
- `discussion_volume`;
- `price_changes`.

All series must be finite, aligned, and contain at least three observations.

### Rejection Rule

Reject when all conditions are true:

1. latest discussion volume is at least twice the prior median;
2. latest institutional block-trade flow is a net outflow;
3. latest price change is non-positive;
4. the AI rating is `Strong Buy`.

## Module 14 CFIA

**Name:** Corporate Financial Integrity Auditor

**Purpose:** Detect operating-cash-flow hallucinations and working-capital
sign inversions in AI-generated financial analysis.

### Sign Convention and Deterministic Equation

`increase_in_net_working_capital` is a balance-sheet movement. A positive value
means more cash is tied up in working capital.

```text
formula_operating_cash_flow
  = net_income
  + non_cash_adjustments
  - increase_in_net_working_capital
```

The ambiguous field name `change_in_working_capital` is rejected because data
providers frequently encode the cash-flow-statement contribution with the
opposite sign.

### Required Inputs

AI output:

- `reported_operating_cash_flow`.

Ground truth:

- `net_income`;
- `non_cash_adjustments`;
- `increase_in_net_working_capital`;
- `reported_operating_cash_flow`;
- `currency`;
- `source_id`;
- `fiscal_period_end`, formatted as ISO-8601 `YYYY-MM-DD`;
- optional non-negative `absolute_tolerance`;
- optional non-negative `relative_tolerance`.

All numeric inputs must be finite. Missing fields are never replaced with zero.

### Ground-Truth Gate

Before evaluating the AI output, the kernel reconciles the reported ground
truth OCF to the deterministic formula. If the source rows fail this tie-out,
execution stops with an input error. A corrupted benchmark cannot be used to
score an AI artifact.

### Rejection and Scoring Rules

- `5.0 / APPROVED`: AI OCF is within the greater of absolute or relative
  tolerance.
- `3.0 / REJECTED`: AI OCF exceeds tolerance without matching the exact
  sign-inversion result.
- `1.0 / REJECTED`: AI OCF reconciles to
  `net_income + non_cash_adjustments + increase_in_net_working_capital`,
  confirming working-capital sign inversion.

The scorecard includes currency, source, fiscal period, formula OCF, reported
ground-truth OCF, AI OCF, tolerance, reconciliation delta, and detected
anomalies.

### Data Boundary

CFIA is a deterministic audit kernel, not a market-data downloader. Network
retrieval, ticker normalization, filing selection, unit conversion, and source
licensing belong in an external ingestion adapter. The kernel refuses missing
or internally inconsistent data and never introduces fabricated fallback
financials.

## Module 15 SCGV

**Name:** Supply Chain GenAI Validator

**Purpose:** Detect AI inventory policies that omit joint demand and lead-time
uncertainty.

### Deterministic Equation

```text
variance
  = average_lead_time * demand_std^2
  + average_demand^2 * lead_time_std^2

safety_stock = z_score * sqrt(variance)

reorder_point
  = average_demand * average_lead_time
  + safety_stock
```

### Required Inputs

AI output:

- `reorder_point`;
- `safety_stock`;
- `methodology`: optional narrative evidence.

Ground truth:

- `average_demand`;
- `average_lead_time`;
- `demand_std`;
- `lead_time_std`;
- `service_level`;
- optional `z_score` for service levels outside the approved lookup table.

Approved lookup values include `90% -> 1.28`, `95% -> 1.65`, `99% -> 2.33`,
and `99.9% -> 3.09`.

### Rejection Rule

Reject when either value deviates by more than the greater of one percent or
0.01 units. Reject independently when the artifact uses the linear shortcut
`z * (demand_std + lead_time_std)`.

## Institutional Scorecard

Every implemented module returns the shared required fields:

```json
{
  "rigor_score": 0.0,
  "data_quality_status": "APPROVED or REJECTED",
  "structured_written_feedback": "Institutional written assessment"
}
```

Module-specific evidence is additive and cannot replace the shared contract.

## Institutional Publication Contract

Kernel scorecards are operational outputs. A publishable research artifact is
a separate, higher-level contract that binds scorecards to timestamped claims,
source references, methodology references, and disclosures.

Every publication must:

1. use an approved document type and Markdown template;
2. carry a unique artifact ID and timezone-aware as-of timestamp;
3. classify each material claim as `FACT`, `INFERENCE`, or `SCENARIO`;
4. cite every fact to a known source;
5. retain the original shared scorecard fields;
6. identify synthetic data, estimates, scenarios, and backtests;
7. pass `src/output_standard.py`.

The complete specification is maintained in
[`docs/OUTPUT_STANDARD.md`](OUTPUT_STANDARD.md). The canonical machine schema
is `schemas/publication_artifact.schema.json`.

## Cross-Market Temporal Contract

Pipeline and publication artifacts must carry one UTC observation instant and
its synchronized projections for US equities, Hong Kong equities, and China
A-shares. DST handling must use IANA timezone data through Python `zoneinfo`.

Scheduled session states must disclose whether an exchange holiday calendar
was applied. The current contract is documented in
[`docs/TEMPORAL_STANDARD.md`](TEMPORAL_STANDARD.md).
