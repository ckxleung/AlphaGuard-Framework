# THE CHINA ALPHA DISPATCH

## TELEMETRY NOTE // {{ISSUE_ID}}

**Artifact ID:** {{ARTIFACT_ID}}  
**As of:** {{AS_OF_ISO_8601_WITH_TIMEZONE}}  
**Generated:** {{GENERATED_AT_ISO_8601_WITH_TIMEZONE}}  
**Author:** {{AUTHOR}}  
**Audit Infrastructure:** {{ENGINE_VERSION}}  
**Classification:** {{CLASSIFICATION}}  
**Data Status:** {{LIVE_OR_SYNTHETIC}}

| Market | Local Timestamp | Zone | Scheduled Session |
|---|---|---|---|
| US Equities | {{US_TIMESTAMP}} | {{US_TIMEZONE_ABBREVIATION}} | {{US_SESSION_STATUS}} |
| Hong Kong Equities | {{HK_TIMESTAMP}} | HKT | {{HK_SESSION_STATUS}} |
| China A-Shares | {{CN_TIMESTAMP}} | CST | {{CN_SESSION_STATUS}} |

> Session status is a weekday schedule projection unless an exchange holiday
> calendar is explicitly identified as applied.

---

### EXECUTIVE SUMMARY

{{STATE_THE_EVENT_THE_VERIFIED_FINDING_AND_THE_DECISION_RELEVANCE}}

Do not include a market statistic, price, valuation, or performance figure
unless it is represented as a sourced claim in the JSON sidecar.

---

### THE ALPHAGUARD PERFORMANCE SCORECARD

| Target | Evaluation Kernel | Rigor Score | Status | Deterministic Finding |
|---|---|---:|---|---|
| {{TARGET}} | {{KERNEL_ID}} | {{SCORE}} / 5.0 | {{STATUS}} | {{FINDING}} |

---

### TECHNICAL DECONSTRUCTION

**Observed condition**

{{SOURCE_BACKED_OBSERVATION}}

**Deterministic test**

```text
{{EQUATION_OR_RULE}}
```

**AlphaGuard result**

{{SEPARATE_INFERENCE_FROM_FACT}}

---

### FORENSIC EVIDENCE

```json
{{VERBATIM_VALIDATED_SCORECARD_OR_EVIDENCE_BLOCK}}
```

---

### STRATEGIC IMPLICATION

{{DESCRIBE_THE_CONDITIONAL_IMPLICATION}}

Label all valuations, forecasts, trades, and expected returns as `SCENARIO`.
State assumptions, invalidation conditions, liquidity constraints, and tail
risk. Do not imply guaranteed performance.

---

### METHODOLOGY AND AUDIT TRAIL

- **Sources:** {{SOURCE_IDS_AND_LINKS}}
- **Methodology:** {{KERNEL_AND_MASTER_SPEC_REFERENCES}}
- **Repository:** https://github.com/ckxleung/AlphaGuard-Framework
- **JSON sidecar:** {{ARTIFACT_JSON_PATH_OR_URL}}

---

### DISCLOSURES

China Alpha Dispatch is an independent research entity. This report is for
informational purposes and is not individualized investment advice. Options,
derivatives, and leveraged strategies involve significant risk, including the
potential loss of capital. Synthetic fixtures, estimates, scenarios, and
backtests are identified explicitly and are not live performance records.
