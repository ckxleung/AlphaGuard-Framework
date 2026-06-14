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
| 09 | FITV | Layer 2 Valuation | Implemented |
| 10 | OAPE | Layer 1 Telemetry | Specified |
| 11 | CVIB | Layer 2 Valuation | Implemented |
| 12 | IRTA | Layer 4 Strategy | Implemented |
| 13 | BMAE | Layer 4 Strategy | Implemented |
| 14 | CFIA | Layer 2 Valuation | Implemented |
| 15 | SCGV | Layer 4 Strategy | Implemented |
| 16 | AMWE | Layer 3 Compliance | Specified |
| 17 | ERCA | Layer 3 Compliance | Specified |
| 18 | IBDV | Layer 2 Valuation | Implemented |

## Specification Contract and Source Reconciliation

Every `Specified` module has a machine-readable contract in
`src/kernel_spec_catalog.py` containing eight mandatory elements:

1. problem statement;
2. AI artifact inputs;
3. ground-truth and provenance inputs;
4. deterministic rules;
5. tolerance policy;
6. rejection conditions;
7. scorecard outputs;
8. declared data boundary.

The imported frontier-benchmark document used a conflicting numbering scheme
for its final modules. AlphaGuard preserves the established canonical IDs:

- source `RSSF` is absorbed as a retail-usability extension of Module 13 BMAE;
- source `FLIB` chained-tool requirements are absorbed by Module 06 TLAB;
- source `SCGV` numbered as 17 maps to canonical Module 15 SCGV;
- canonical Module 17 remains ERCA.

Source examples are treated as design notes, not production code. Silent file
fallbacks, raw keyword-only grading, floating-point ledger reconciliation, live
unrecorded lookups, and inconsistent status labels are explicitly excluded.

The four functional layers are the kernel architecture. The monitoring control
plane may additionally assign targets to commercial cohorts such as
`FOUNDATIONAL_API`, `ENTERPRISE_FINTECH_AGENT`, and `COMPUTE_INFRASTRUCTURE`;
those cohorts do not change canonical module IDs or layer ownership.

## Module 01 FRTE

**Purpose:** Compare equivalent prior- and current-period filing sections and
identify material risk disclosures omitted or invented by an AI summary.

**Contract:** Inputs include the AI summary, comparable filing texts, section
boundaries, source IDs, period ends, and a materiality rubric. The engine
classifies added, removed, and modified disclosure units, then binds each AI
claim to an evidence span. Exact source identity is required; concept matching
and materiality weights are fixture-controlled.

**Reject when:** a material new risk is omitted, the AI invents a change, or
the filings are not comparable by form, period, section, or provenance.

## Module 02 APAC

**Purpose:** Audit multi-step APAC operating, options-skew, regulatory, and
credit-risk transmission reasoning.

**Contract:** Inputs include dated operating metrics, one normalized option
chain snapshot, export-control sources, entity linkages, market calendars, and
the AI transmission chain. The engine recalculates the declared delta-bucket IV
skew and validates every causal edge. Numeric results default to a 0.5% relative
tolerance; dates, entities, expiries, currencies, and delta conventions must
match exactly.

**Reject when:** a required calculation or evidence step is skipped, market
snapshots are mixed, or a regulatory statement is unsupported or temporally
invalid.

## Module 03 AMDG

**Purpose:** Evaluate wealth-management and institutional office deliverables
for financial accuracy, source traceability, and rendered visual discipline.

**Contract:** Recalculate compounding, allocation, fee, tax, and cash-flow
outputs from declared assumptions. Inspect action headlines, source footnotes,
units, color limits, clipping, and table readability using both package metadata
and render evidence. Numerical defects carry greater weight than cosmetic ones.

**Reject when:** a material calculation fails, critical content is clipped or
unreadable, or assumptions and source references are missing.

## Module 04 CASS

**Purpose:** Test whether a strategy resolves conflicts among controlled
stakeholder personas under explicit resource and policy constraints.

**Contract:** Map recommendations to affected personas, identify incompatible
commitments, and require an owner, trade-off, decision, and escalation path for
every unresolved conflict. Non-negotiable constraints are exact; preferences
use scenario-declared weights.

**Reject when:** a mandatory constraint is violated, incompatible commitments
are presented as consensus, or a material conflict lacks resolution.

## Module 05 SFRA

**Purpose:** Measure long-context retrieval and cross-reference integrity in
SEC filing footnotes.

**Contract:** Resolve benchmark questions through declared footnote, table, and
cross-reference graphs. Verify citations and numbers against source coordinates
and report accuracy by document-position bucket to expose lost-in-the-middle
degradation.

**Reject when:** a required reference is unresolved, the answer contradicts its
linked table, or filing identity and source coordinates are absent.

## Module 06 TLAB

**Purpose:** Audit generated API integrations and chained tool execution
against a versioned technical contract.

**Contract:** Parse generated code and structured execution traces. Verify API
version, endpoint, method, payload, authentication, retry behavior, error
handling, and mandatory extract/search/calculate steps. Missing specification
files fail closed and are never replaced with invented defaults.

**Reject when:** generated code targets an incompatible schema, omits security
or rate-limit controls, skips a mandatory step, or reports a fabricated tool
success.

## Module 07 BLSB

**Purpose:** Evaluate GTM and operating-strategy artifacts for empirical
grounding, actionability, and downside controls.

**Contract:** Trace quantified claims to sources and evaluate segment choice,
value proposition, channel, unit economics, resources, owner, timing, risk
mitigation, and exit criteria. Buzzword density is only a secondary indicator.

**Reject when:** a material recommendation lacks evidence or ownership, unit
economics and capacity are absent, or promotional language replaces measurable
actions.

## Module 08 FOAS

**Purpose:** Reconcile ledgers, trial balances, adjustments, and internal-control
artifacts to cent-level accounting identities.

**Contract:** Use decimal arithmetic to aggregate debits and credits by entity,
account, currency, and period. Reconcile subledgers to the trial balance and
every adjustment to balanced source rows. The default monetary tolerance is
0.01 in the declared currency.

**Reject when:** the ledger is out of balance, an adjustment lacks traceability,
or currencies, entities, or periods are mixed without normalization.

## Module 09 FITV

**Purpose:** Validate bond price, modified duration, DV01, and the written
rate-risk conclusion under one declared market convention.

**Contract:** FITV v1 accepts ordered contractual cash flows with ISO-8601
payment dates, an ISO-8601 settlement date, `ACT/365F`, coupon frequency of 1,
2, 4, or 12, yield to maturity, face value, currency, clean-or-dirty price
basis, accrued interest, and a registered source ID.

For each cash flow:

```text
t_i = (payment_date_i - settlement_date) / 365
PV_i = cash_flow_i / (1 + y / m) ^ (m * t_i)
```

The deterministic metrics are:

```text
dirty_price = sum(PV_i)
clean_price = dirty_price - accrued_interest
Macaulay duration = sum(t_i * PV_i) / dirty_price
Modified duration = Macaulay duration / (1 + y / m)
DV01 = Modified duration * dirty_price * 0.0001
```

AI output must provide price, modified duration, DV01, price basis, day-count
convention, coupon frequency, and a controlled rate-risk conclusion:
`RATES_UP_PRICE_DOWN` or `RATES_DOWN_PRICE_UP`.

**Tolerance:** Price, duration, and DV01 each default to 0.5% relative error and
may be overridden independently with non-negative fixture values.

**Reject when:** a metric exceeds its tolerance, a declared convention differs,
the discount base is non-positive, the schedule is invalid, or the rate-risk
conclusion has the wrong sign.

## Module 10 OAPE

**Purpose:** Perform deterministic pairwise evaluation of XLSX, DOCX, and PPTX
artifacts.

**Contract:** Inspect formulas, package relationships, slide geometry, fonts,
metadata, and controlled render results. Apply a severity matrix to both
candidates and permit a tie. Metadata alone cannot establish absence of visual
overlap.

**Reject when:** a candidate contains broken formulas, invalid relationships,
clipping or overlap, comparison settings are not equivalent, or an arbitrary
winner is selected from equal scores.

## Module 11 CVIB

**Purpose:** Audit DCF and trading-comparable outputs against declared valuation
assumptions.

**Contract:** Recalculate forecast cash-flow present values, terminal value,
enterprise-to-equity bridge, diluted per-share value, and selected multiples.
WACC must exceed terminal growth. Currency, valuation date, share basis, and
trailing-versus-forward denominator must remain consistent. Output tolerance
may default to 2% while equation-level tolerances remain stricter.

**Reject when:** the DCF is mathematically undefined, outputs exceed tolerance,
or the AI mixes dates, currencies, numerator bases, or denominator periods.

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

## Module 16 AMWE

**Purpose:** Detect temporal leakage, invalid validation splits, and misleading
metrics in applied ML workflows.

**Contract:** Compare feature-availability times with prediction and target
times, inspect split indices, and require chronological or purged validation
for time-dependent or overlapping-label datasets. Materially imbalanced
classification cannot be optimized and reported using accuracy alone.

**Reject when:** future information enters a feature or preprocessing statistic,
random K-fold is used without an approved exception, or the selected metric is
misaligned with the target distribution.

## Module 17 ERCA

**Purpose:** Audit enterprise AI controls against a source-identified
COSO-style risk, control, and compliance matrix.

**Contract:** Map each material risk to a control objective, owner, frequency,
evidence, and escalation path. Distinguish control design from operating
effectiveness. Regulatory requirements must identify jurisdiction, effective
date, and primary source.

**Reject when:** a mandatory risk lacks a control or owner, operating
effectiveness is claimed from design documentation alone, or regulatory
provenance is incomplete.

## Module 18 IBDV

**Name:** Investment-Banking Deal Validation

**Purpose:** Detect enterprise-value bridge errors in M&A precedent
transactions, transaction summaries, and AI-generated valuation work.

### Deterministic Equation

```text
enterprise_value
  = equity_value
  + total_debt
  - cash_and_equivalents
  + preferred_stock
  + non_controlling_interests
```

All components must use the same currency and valuation date. Equity value,
debt, cash, preferred stock, and non-controlling interests are non-negative.
Enterprise value itself may be negative for a net-cash company.

### Required Inputs

AI output:

- `calculated_enterprise_value`.

Ground truth:

- `equity_value`;
- `total_debt`;
- `cash_and_equivalents`;
- `preferred_stock`;
- `non_controlling_interests`;
- `reported_enterprise_value`;
- `currency`, as a three-letter alphabetic code;
- `equity_value_basis`, identifying market capitalization, offer
  consideration, or transaction equity value;
- `source_id`;
- `valuation_date`, formatted as ISO-8601 `YYYY-MM-DD`;
- optional non-negative `absolute_tolerance`;
- optional non-negative `relative_tolerance`.

### Ground-Truth Gate

The kernel first reconciles `reported_enterprise_value` to the deterministic
bridge. If the supplied benchmark does not tie, execution stops. Missing
components are never silently replaced with zero.

### Omission Detection and Scoring

- `5.0 / APPROVED`: AI EV reconciles within tolerance.
- `3.0 / REJECTED`: AI EV exceeds tolerance without matching a deterministic
  omission pattern.
- `1.5 / REJECTED`: AI EV exactly matches a bridge omitting either preferred
  stock or non-controlling interests.
- `1.0 / REJECTED`: AI EV exactly matches
  `equity_value + total_debt - cash_and_equivalents`, omitting both preferred
  stock and non-controlling interests.

The scorecard reports the omitted components, equation delta, source,
valuation date, currency, equity-value basis, every bridge component, and the
ground-truth reconciliation delta.

### Declared Bridge Scope

This version validates the five-component bridge above. Lease liabilities,
unfunded pensions, associate investments, tax assets, earn-outs, and other
debt-like or non-operating adjustments are not silently inferred. A transaction
requiring those adjustments must extend the ingestion schema and deterministic
equation before it is evaluated.

IBDV does not download market data or fabricate missing capital structure
items. Filing selection, transaction-date share counts, FX normalization,
source licensing, and deal-term extraction belong in a provenance-aware
ingestion adapter.

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
