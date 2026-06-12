# AlphaGuard Institutional Output Standard

## Purpose

AlphaGuard is an automated system for producing auditable research artifacts,
not an unstructured content generator. Every publishable output must therefore
have two synchronized forms:

1. a human-readable Markdown report built from an approved template;
2. a machine-readable JSON sidecar validated by `src/output_standard.py`.

The Markdown file communicates the research. The JSON sidecar proves what was
claimed, which evidence supported it, which kernel evaluated it, and when the
underlying data was current.

## Approved Document Types

### Telemetry Note

Use for event-driven earnings, filing, market-microstructure, supply-chain, or
model-behavior anomalies. The expected reading time is five to ten minutes.
Start from `templates/telemetry_note.md`.

Required sections:

1. document control;
2. executive summary;
3. AlphaGuard performance scorecard;
4. technical deconstruction;
5. forensic evidence;
6. strategic implication;
7. methodology and audit trail;
8. disclosures.

### Deep-Dive Whitepaper

Use for multi-company, cross-market, or quarterly thematic research. Start
from `templates/deep_dive_whitepaper.md`.

Required sections:

1. document control;
2. investment question and scope;
3. executive findings;
4. evidence base and methodology;
5. market or industry architecture;
6. company-level forensic findings;
7. valuation or scenario analysis;
8. risks, disconfirming evidence, and invalidation conditions;
9. audit trail;
10. disclosures.

## Fixed Shell, Dynamic Core

Section order, naming, document control, evidence labels, and disclosures are
fixed. Company names, data, equations, findings, and scenarios are dynamic.
Sections may be marked `NOT APPLICABLE`, but required sections may not be
deleted.

This fixed shell gives institutional readers a stable retrieval pattern while
preserving analytical flexibility.

## Visual and Editorial Rules

- Use restrained Markdown headings, tables, blockquotes, equations, and code.
- Do not use emoji, decorative icons, engagement bait, or promotional slogans.
- Use direct institutional English. Separate observation from interpretation.
- Use ISO-8601 timestamps with explicit timezone offsets.
- State currencies, units, fiscal periods, and market sessions explicitly.
- Label synthetic fixtures, estimates, scenarios, and backtests as such.
- Never present model output as verified market fact.
- Never publish a price, yield, failure rate, valuation, or performance claim
  without a source reference and as-of timestamp.

## Claim Taxonomy

Every material assertion in the JSON sidecar must be assigned one type:

| Type | Meaning | Minimum evidence |
|---|---|---|
| `FACT` | Externally observable or reported value | At least one source |
| `INFERENCE` | AlphaGuard interpretation of evidence | Source and methodology |
| `SCENARIO` | Conditional forecast, valuation, or strategy case | Methodology and assumptions |

Facts and inferences must not be blended into one sentence. A statement such
as "revenue was USD 10 billion, proving the equity is undervalued" must become
two claims: one `FACT` and one `INFERENCE`.

## Source Standard

Each source requires:

- a stable `source_id`;
- title;
- HTTP(S) URL;
- `accessed_at` timestamp with timezone.

Preferred evidence order:

1. regulatory filings and exchange disclosures;
2. company investor-relations material;
3. official statistical or regulatory datasets;
4. primary market-data feeds;
5. reputable secondary research.

Social-media evidence may support behavioral analysis but must not be treated
as a substitute for filings, transaction data, or official disclosures.

## Scorecard Standard

Every published finding must retain the shared `BaseAuditor` fields:

```json
{
  "kernel_id": "Module_15_SCGV",
  "target": "AVGO",
  "rigor_score": 2.1,
  "data_quality_status": "REJECTED",
  "structured_written_feedback": "The proposed reorder point omits lead-time variance."
}
```

Module-specific evidence may be added. It may not replace the shared fields.
Raw scorecards must not be rewritten to make a narrative more persuasive.

## Machine-Readable Contract

The canonical schema is
`schemas/publication_artifact.schema.json`. Runtime validation is implemented
in `src/output_standard.py`.

Validate an artifact before publication:

```bash
python3 src/output_standard.py examples/publication_artifact.example.json
```

Required top-level fields:

- `schema_version`;
- `artifact_id`;
- `document_type`;
- `title`;
- `as_of`;
- `generated_at`;
- `telemetry_timestamp_matrix`;
- `engine_version`;
- `classification`;
- `executive_summary`;
- `claims`;
- `sources`;
- `scorecards`;
- `disclosures`.

## Publication Acceptance Gates

An artifact is publishable only when all gates pass:

1. repository validation succeeds;
2. every scorecard satisfies `BaseAuditor`;
3. every `FACT` cites at least one known source;
4. every claim cites methodology;
5. timestamps include timezone;
6. required disclosures are true;
7. synthetic data is explicitly identified;
8. no placeholder values remain in the final report;
9. Markdown and JSON use the same artifact ID and as-of time;
10. a human reviewer confirms that the prose does not overstate the evidence.

The timestamp matrix must satisfy
[`docs/TEMPORAL_STANDARD.md`](TEMPORAL_STANDARD.md). All three local market
clocks must reconcile to one UTC instant, and that instant must equal the
publication's `as_of` timestamp. A weekday schedule projection must not be
described as an exchange-verified holiday calendar.

## Premium Gateway

A subscription gateway may separate public and premium sections, but it must
not hide required disclosures, manipulate scorecards, or imply guaranteed
returns. Strategy parameters behind the gateway remain subject to the same
source, timestamp, scenario, and risk-disclosure rules.

## Required Disclaimer

Every report must state that China Alpha Dispatch is an independent research
entity, that the material is for informational purposes, and that derivatives
or options involve significant risk where applicable. Nothing in the output
contract converts research into individualized investment advice.
