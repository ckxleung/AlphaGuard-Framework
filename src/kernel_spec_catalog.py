# -*- coding: utf-8 -*-
"""Machine-readable specification catalog for all eighteen AlphaGuard kernels."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.module_manifest import MODULE_SPECS


@dataclass(frozen=True, slots=True)
class KernelSpecification:
    """Reviewable delivery contract for one evaluation kernel."""

    module_id: int
    code: str
    problem_statement: str
    ai_inputs: tuple[str, ...]
    ground_truth_inputs: tuple[str, ...]
    deterministic_rules: tuple[str, ...]
    tolerance_policy: str
    rejection_conditions: tuple[str, ...]
    outputs: tuple[str, ...]
    data_boundary: str
    source_aliases: tuple[str, ...] = ()


KERNEL_SPECIFICATIONS: Final[tuple[KernelSpecification, ...]] = (
    KernelSpecification(
        1,
        "FRTE",
        "Detect newly introduced filing risks that an AI quarterly-summary artifact omits or invents.",
        ("ai_summary", "claimed_risk_deltas"),
        (
            "prior_period_filing_text",
            "current_period_filing_text",
            "section_boundaries",
            "materiality_rubric",
            "source_ids",
            "period_end_dates",
        ),
        (
            "Normalize comparable filing sections before computing added, removed, and modified disclosure units.",
            "Match summary claims to source-backed deltas using configured concepts and evidence spans, not raw keyword counts alone.",
            "Separate omissions, unsupported additions, and correctly covered deltas.",
        ),
        "Exact source-span identity for facts; configurable concept-match threshold and materiality weights must be declared by fixture.",
        (
            "A material new risk delta has no supported AI-summary coverage.",
            "The AI summary asserts a risk change absent from the current-versus-prior filing delta.",
            "Periods, filing sections, or provenance are not comparable.",
        ),
        (
            "material_delta_count",
            "omitted_material_deltas",
            "unsupported_ai_claims",
            "coverage_ratio",
            "rigor_score",
        ),
        "Filing retrieval, amendment selection, OCR, and section normalization occur in a provenance-aware ingestion adapter.",
        ("Fin-LLM-RedTeaming-Engine",),
    ),
    KernelSpecification(
        2,
        "APAC",
        "Audit multi-step APAC supply-chain, options-skew, and regulatory contagion reasoning.",
        ("ai_transmission_chain", "ai_iv_skew", "ai_credit_risk_conclusion"),
        (
            "dated_operating_metrics",
            "option_chain_snapshot",
            "export_control_sources",
            "entity_linkage_graph",
            "market_calendars",
        ),
        (
            "Calculate the declared delta-bucket implied-volatility skew from one timestamped option-chain snapshot.",
            "Trace each transmission edge from operating exposure through market signal to credit implication.",
            "Bind regulatory statements to effective dates and primary sources.",
        ),
        "Numeric calculations must remain within the fixture-declared 0.5% relative tolerance; dates and entity links require exact agreement.",
        (
            "A required calculation or evidence-retrieval step is skipped.",
            "The options inputs mix timestamps, expiries, currencies, or delta conventions.",
            "A regulatory assertion is unsupported or temporally invalid.",
        ),
        (
            "iv_skew_delta",
            "validated_transmission_edges",
            "unsupported_edges",
            "temporal_integrity_status",
            "rigor_score",
        ),
        "Live prices and regulatory search results must be captured upstream with timestamps; the kernel never performs an unrecorded live lookup.",
        ("APAC-AI-SupplyChain-Contagion",),
    ),
    KernelSpecification(
        3,
        "AMDG",
        "Evaluate wealth-management and institutional deliverables for numerical and visual decision quality.",
        ("artifact_manifest", "calculated_outputs", "presentation_metadata"),
        (
            "approved_template_rules",
            "financial_assumptions",
            "expected_calculations",
            "render_inspection_results",
        ),
        (
            "Recalculate compounding, allocation, fee, tax, and cash-flow outputs from declared assumptions.",
            "Check action-oriented headlines, source footnotes, unit labels, color limits, clipping, and table readability.",
            "Treat numerical defects as higher severity than cosmetic defects.",
        ),
        "Financial outputs use fixture-level currency precision; layout thresholds and brand rules are explicit configuration values.",
        (
            "A material financial output does not reconcile.",
            "A slide or workbook region is clipped, unreadable, or missing a required source.",
            "The artifact uses undeclared assumptions or inconsistent units.",
        ),
        (
            "calculation_defects",
            "visual_defects",
            "source_traceability_ratio",
            "institutional_readiness_status",
            "rigor_score",
        ),
        "Office-file parsing and rendering are performed by controlled adapters; metadata alone cannot prove absence of visual overlap.",
        ("FAARE", "Personal-Finance-Aesthetic-Rigor-Auditor"),
    ),
    KernelSpecification(
        4,
        "CASS",
        "Test whether an AI strategy resolves explicit conflicts among stakeholder constraints.",
        ("proposed_strategy", "stakeholder_responses", "decision_log"),
        (
            "persona_constraints",
            "resource_limits",
            "non_negotiable_policies",
            "scenario_documents",
        ),
        (
            "Map every material recommendation to affected personas and constraints.",
            "Detect mutually incompatible commitments and unsupported claims of consensus.",
            "Require an owner, decision, trade-off, and escalation path for unresolved conflicts.",
        ),
        "Constraint satisfaction is exact for non-negotiable rules; weighted preferences use scenario-declared priorities.",
        (
            "A non-negotiable constraint is violated.",
            "Conflicting stakeholder commitments are presented as simultaneously achievable.",
            "A material conflict lacks an explicit resolution or escalation path.",
        ),
        (
            "constraint_violations",
            "unresolved_conflicts",
            "stakeholder_feedback_matrix",
            "reconciliation_required",
            "rigor_score",
        ),
        "Persona definitions and constraints are controlled test fixtures; the kernel does not invent stakeholder preferences.",
        ("Consulting-AI-Scenario-Sandbox",),
    ),
    KernelSpecification(
        5,
        "SFRA",
        "Measure long-context retrieval and cross-reference integrity in SEC filing footnotes.",
        ("ai_answers", "cited_evidence_spans"),
        (
            "filing_text",
            "footnote_boundaries",
            "table_cells",
            "cross_reference_graph",
            "benchmark_questions",
            "source_id",
        ),
        (
            "Resolve each benchmark question through the declared footnote and table cross-reference graph.",
            "Verify cited spans and numerical values against source coordinates.",
            "Report retrieval performance by document position to expose lost-in-the-middle degradation.",
        ),
        "Text citations require exact source coordinates; numeric answers use fixture-declared accounting precision.",
        (
            "A required cross-reference cannot be resolved.",
            "The answer cites an unrelated span or contradicts the linked table.",
            "Source coordinates or filing identity are missing.",
        ),
        (
            "context_retrieval_integrity",
            "unresolved_references",
            "position_bucket_accuracy",
            "citation_precision",
            "rigor_score",
        ),
        "SEC retrieval, HTML-to-text conversion, and table extraction are upstream processes with retained source coordinates.",
        ("SEC-Filings-Reasoning-Auditor",),
    ),
    KernelSpecification(
        6,
        "TLAB",
        "Audit generated API integrations and chained tool execution against a versioned technical contract.",
        ("generated_code", "declared_api_version", "execution_trace"),
        (
            "api_schema",
            "breaking_change_manifest",
            "required_headers",
            "rate_limit_policy",
            "mandatory_tool_steps",
        ),
        (
            "Parse code and structured traces rather than relying only on substring searches.",
            "Verify endpoint, method, payload, authentication, retry, and error-handling behavior against one API version.",
            "Check required extract, search, and calculation steps in order when a benchmark declares a chained workflow.",
        ),
        "Schema fields and step order require exact agreement; retry timing and numeric tool outputs use declared fixture tolerances.",
        (
            "Generated code targets an incompatible API version or payload.",
            "Authentication, rate-limit handling, or a mandatory tool step is absent.",
            "The execution trace contains an undeclared or fabricated successful tool result.",
        ),
        (
            "schema_violations",
            "missing_execution_steps",
            "breaking_change_exposure",
            "instruction_following_score",
            "rigor_score",
        ),
        "API schemas and execution traces are required inputs. Missing files fail closed and are never replaced with fabricated defaults.",
        ("Tech-LLM-Architecture-Benchmark", "FLIB"),
    ),
    KernelSpecification(
        7,
        "BLSB",
        "Evaluate GTM and operating strategy artifacts for empirical grounding and downside controls.",
        ("strategy_memo", "claims", "action_plan"),
        (
            "market_evidence",
            "customer_segments",
            "resource_constraints",
            "approved_strategy_rubric",
        ),
        (
            "Trace quantified claims to evidence and distinguish facts, inferences, and scenarios.",
            "Evaluate segment choice, value proposition, channel, economics, owner, timing, and exit criteria.",
            "Use buzzword density only as a secondary indicator, never as the decisive rule.",
        ),
        "Claim values use source-specific tolerances; required strategy fields and evidence links require exact presence.",
        (
            "A material recommendation has no evidence or accountable owner.",
            "Unit economics, resource capacity, or downside mitigation is absent.",
            "Promotional language substitutes for measurable actions and thresholds.",
        ),
        (
            "unsupported_claims",
            "missing_operating_controls",
            "actionability_ratio",
            "strategy_readiness_status",
            "rigor_score",
        ),
        "Market evidence must be supplied with provenance and dates; the kernel does not infer current market facts from prose.",
        ("BPS-LLM-Strategy-Benchmark",),
    ),
    KernelSpecification(
        8,
        "FOAS",
        "Reconcile ledger and control artifacts to cent-level accounting identities and traceable source rows.",
        ("ai_reconciliation", "proposed_adjustments", "control_narrative"),
        (
            "ledger_rows",
            "trial_balance",
            "account_mapping",
            "currency",
            "period_end",
            "source_id",
        ),
        (
            "Aggregate debits and credits with decimal arithmetic by entity, account, currency, and period.",
            "Reconcile subledger totals to the trial balance and each proposed adjustment to source rows.",
            "Separate rounding differences from unexplained variances.",
        ),
        "Default monetary tolerance is 0.01 in the declared currency unless the fixture explicitly defines another precision.",
        (
            "Debits and credits exceed the declared tolerance.",
            "A proposed adjustment lacks balanced entries or source-row traceability.",
            "Currencies, entities, or accounting periods are mixed without normalization.",
        ),
        (
            "is_balanced",
            "variance_delta",
            "unreconciled_accounts",
            "adjustment_traceability_status",
            "rigor_score",
        ),
        "Ledger extraction and account mapping are upstream controls; floating-point arithmetic is not permitted for monetary reconciliation.",
        ("FinOps-Audit-Artifact-Evaluator",),
    ),
    KernelSpecification(
        9,
        "FITV",
        "Validate bond price, modified duration, and DV01 calculations under a declared market convention.",
        ("ai_price", "ai_modified_duration", "ai_dv01", "trade_thesis"),
        (
            "cash_flow_schedule",
            "yield_to_maturity",
            "settlement_date",
            "day_count_convention",
            "coupon_frequency",
            "face_value",
            "currency",
        ),
        (
            "Discount every contractual cash flow using the declared compounding and day-count convention.",
            "Calculate Macaulay duration, modified duration, and DV01 from the same clean-or-dirty price basis.",
            "Check that the written rate-risk conclusion has the correct sign and scale.",
        ),
        "Price, duration, and DV01 tolerances are separately declared; the reference fixture may default to 0.5% relative error.",
        (
            "Any core metric exceeds its tolerance.",
            "The AI mixes clean price, dirty price, yield convention, or settlement basis.",
            "The rate-shock narrative contradicts the calculated duration exposure.",
        ),
        (
            "analytical_price",
            "analytical_modified_duration",
            "analytical_dv01",
            "metric_deltas",
            "rigor_score",
        ),
        "Curve construction and live RFQ ingestion occur upstream; all pricing conventions must accompany the benchmark input.",
        ("Fixed-Income-Trading-Validator",),
    ),
    KernelSpecification(
        10,
        "OAPE",
        "Compare office artifacts using structural, calculation, and rendered-layout evidence.",
        ("candidate_a_manifest", "candidate_b_manifest"),
        (
            "approved_style_guide",
            "formula_expectations",
            "render_inspection_a",
            "render_inspection_b",
        ),
        (
            "Inspect workbook formulas, document relationships, slide geometry, fonts, and required metadata.",
            "Use rendered evidence to detect clipping and overlap that package metadata cannot reveal.",
            "Apply a deterministic defect severity matrix and permit a tie.",
        ),
        "Formula correctness is exact after normalization; visual thresholds and font rules are configuration-controlled.",
        (
            "A candidate contains broken formulas, invalid relationships, clipping, or overlapping critical content.",
            "The comparison lacks equivalent render settings or required source artifacts.",
            "A winner is selected despite equal weighted defect scores.",
        ),
        (
            "selected_winner",
            "candidate_a_defects",
            "candidate_b_defects",
            "comparison_basis",
            "rigor_score",
        ),
        "Office parsing and rendering require controlled versions of openpyxl, python-docx, python-pptx, and a rendering adapter.",
        ("Office-Artifact-Pairwise-Evaluator",),
    ),
    KernelSpecification(
        11,
        "CVIB",
        "Audit DCF and trading-comparable outputs against declared valuation assumptions.",
        ("ai_enterprise_value", "ai_equity_value", "ai_price_per_share", "ai_multiples"),
        (
            "forecast_free_cash_flows",
            "wacc",
            "terminal_growth_rate",
            "net_debt",
            "diluted_shares",
            "comparable_company_metrics",
            "valuation_date",
        ),
        (
            "Discount forecast cash flows and terminal value using WACC strictly greater than terminal growth.",
            "Bridge enterprise value to equity value and per-share value using one valuation date and share basis.",
            "Recalculate selected comparable multiples from source numerators and denominators.",
        ),
        "Default valuation-output tolerance is 2% relative error, with stricter equation-level tolerances declared by fixture.",
        (
            "WACC is not greater than terminal growth or a required input is non-positive.",
            "AI outputs exceed tolerance or mix valuation dates, currencies, or share-count bases.",
            "A multiple uses an inconsistent enterprise/equity numerator or trailing/forward denominator.",
        ),
        (
            "ground_truth_enterprise_value",
            "ground_truth_equity_value",
            "ground_truth_price_per_share",
            "valuation_deltas",
            "rigor_score",
        ),
        "Forecast selection, comparable-company screening, FX conversion, and market-data licensing remain upstream responsibilities.",
        ("Junior-Investment-Analyst-Valuation-Benchmarker",),
    ),
    KernelSpecification(
        12,
        "IRTA",
        "Detect investment theses whose growth path breaches physical capacity or unsupported long-run assumptions.",
        ("revenue_forecast", "investment_thesis"),
        (
            "current_capacity",
            "capex_additions",
            "capital_efficiency",
            "max_utilization",
            "blended_asp",
        ),
        (
            "Calculate annual physical revenue ceilings from capacity, cumulative CapEx, utilization, and blended ASP.",
            "Calculate forecast CAGR and implied utilization by year.",
        ),
        "Any annual capacity breach is decisive; optional terminal and risk thresholds must be explicitly supplied by the benchmark.",
        (
            "Forecast revenue exceeds the physical ceiling in any year.",
        ),
        (
            "capacity_ceiling_breached",
            "implied_utilization_rate",
            "forecast_cagr",
            "breached_years",
            "rigor_score",
        ),
        "Expansion announcements and ASP normalization are ingested upstream. Terminal-value and regulatory-risk tests require a future schema extension.",
        ("Senior-Investment-Analyst-Thesis-Auditor",),
    ),
    KernelSpecification(
        13,
        "BMAE",
        "Separate retail sentiment amplification from institutionally confirmed price and flow signals.",
        ("sentiment_changes", "rating"),
        (
            "block_trades_outflow",
            "retail_orderflow_imbalance",
            "discussion_volume",
            "price_changes",
        ),
        (
            "Calculate covariance between sentiment change and institutional-flow-to-retail-imbalance ratio.",
            "Calculate discussion-volume inflation and signal-to-noise measures on aligned observations.",
            "Reject bullish ratings when discussion spikes while institutional flow and price confirmation diverge.",
        ),
        "Series alignment is exact; the default discussion-spike threshold is 2.0 times prior median and must be versioned.",
        (
            "A Strong Buy coincides with a discussion spike, institutional outflow, and non-positive price confirmation.",
            "Input series are misaligned, non-finite, or contain a zero denominator.",
        ),
        (
            "noise_inflation_ratio",
            "signal_to_noise_db",
            "signal_purity_coefficient",
            "noise_filter_failed",
            "rigor_score",
        ),
        "Social and trade feeds are timestamped upstream. The kernel does not infer institutional identity from unclassified volume.",
        ("RSSF", "Retail-Sentiment-Signal-Filter"),
    ),
    KernelSpecification(
        14,
        "CFIA",
        "Detect operating-cash-flow hallucinations and working-capital sign inversions.",
        ("reported_operating_cash_flow",),
        (
            "net_income",
            "non_cash_adjustments",
            "increase_in_net_working_capital",
            "reported_operating_cash_flow",
            "currency",
            "source_id",
            "fiscal_period_end",
        ),
        (
            "Calculate operating cash flow as net income plus non-cash adjustments minus the increase in net working capital.",
            "Reconcile the supplied ground truth before evaluating the AI value.",
            "Test the deterministic opposite-sign result to identify a working-capital sign inversion.",
        ),
        "Use the greater of 0.01 absolute currency units and 0.000001 relative error unless overridden by a non-negative fixture value.",
        (
            "The supplied benchmark fails its own cash-flow identity.",
            "AI operating cash flow exceeds tolerance.",
            "AI operating cash flow matches the opposite working-capital sign convention.",
        ),
        (
            "formula_operating_cash_flow",
            "reconciliation_delta",
            "sign_inversion_detected",
            "data_quality_status",
            "rigor_score",
        ),
        "Statement retrieval, unit conversion, and filing selection are upstream; missing values are never replaced with zero.",
        ("Corporate-Finance-Intelligence-Auditor",),
    ),
    KernelSpecification(
        15,
        "SCGV",
        "Validate safety stock and reorder points under joint demand and lead-time uncertainty.",
        ("reorder_point", "safety_stock", "methodology"),
        (
            "average_demand",
            "average_lead_time",
            "demand_std",
            "lead_time_std",
            "service_level",
            "z_score",
        ),
        (
            "Calculate variance as average lead time times demand variance plus squared average demand times lead-time variance.",
            "Calculate safety stock as z-score times the square root of variance.",
            "Calculate reorder point as average demand times average lead time plus safety stock.",
        ),
        "Use the greater of 0.01 absolute units and 1% relative error for both safety stock and reorder point.",
        (
            "Either calculated value exceeds tolerance.",
            "The methodology uses a linear sum of standard deviations.",
            "The service level has no approved or explicitly supplied positive z-score.",
        ),
        (
            "inventory_stockout_risk_pct",
            "equation_deviation_delta",
            "linear_shortcut_detected",
            "data_quality_status",
            "rigor_score",
        ),
        "Demand and lead-time distributions are supplied benchmark assumptions; multi-echelon correlation requires a future schema extension.",
        ("SCGV-17", "Supply-Chain-GenAI-Validator"),
    ),
    KernelSpecification(
        16,
        "AMWE",
        "Detect temporal leakage, invalid validation splits, and misleading metrics in applied ML workflows.",
        ("pipeline_metadata", "training_code_metadata", "reported_metrics"),
        (
            "dataset_profile",
            "feature_availability_times",
            "target_times",
            "split_indices",
            "approved_metrics",
        ),
        (
            "Verify every feature is available no later than its prediction timestamp.",
            "Require chronological or purged splitting for time-series and overlapping-label datasets.",
            "Evaluate imbalanced classification with approved discrimination and calibration metrics, not accuracy alone.",
        ),
        "Timestamp ordering and split membership are exact; metric tolerances are declared by benchmark fixture.",
        (
            "A feature or preprocessing statistic uses future observations.",
            "Random K-fold is used on time-dependent rows without an approved exception.",
            "Accuracy is the sole optimized metric for a materially imbalanced target.",
        ),
        (
            "leakage_events",
            "split_integrity_status",
            "metric_alignment_status",
            "technical_quality_score",
            "rigor_score",
        ),
        "The kernel audits supplied metadata and split indices; proving runtime pipeline behavior requires captured execution traces.",
        ("Applied-ML-Workflow-Evaluator",),
    ),
    KernelSpecification(
        17,
        "ERCA",
        "Audit enterprise AI controls against a source-identified COSO-style risk and compliance matrix.",
        ("control_narrative", "claimed_control_coverage", "evidence_references"),
        (
            "control_objectives",
            "risk_register",
            "required_approvals",
            "evidence_inventory",
            "regulatory_sources",
            "assessment_date",
        ),
        (
            "Map each material risk to a control objective, owner, frequency, evidence, and escalation path.",
            "Verify claimed controls against supplied evidence and identify design versus operating-effectiveness gaps.",
            "Bind regulatory requirements to jurisdiction, effective date, and primary source.",
        ),
        "Mandatory controls require exact coverage; weighted residual-risk tolerances are declared by the control matrix.",
        (
            "A mandatory risk has no control owner or evidence.",
            "The AI claims operating effectiveness from design documentation alone.",
            "A regulatory requirement lacks jurisdiction, effective date, or source.",
        ),
        (
            "control_coverage_ratio",
            "design_gaps",
            "operating_effectiveness_gaps",
            "residual_risk_status",
            "rigor_score",
        ),
        "The public kernel consumes sanitized control evidence. Live policy libraries and proprietary control matrices remain external.",
        ("Enterprise-Risk-Compliance-Audit",),
    ),
    KernelSpecification(
        18,
        "IBDV",
        "Audit enterprise-value bridges and transaction multiples for capital-structure and period mismatches.",
        ("calculated_enterprise_value",),
        (
            "equity_value",
            "total_debt",
            "cash_and_equivalents",
            "preferred_stock",
            "non_controlling_interests",
            "reported_enterprise_value",
            "currency",
            "equity_value_basis",
            "valuation_date",
            "source_id",
        ),
        (
            "Calculate enterprise value as equity value plus debt minus cash plus preferred stock and non-controlling interests.",
            "Reconcile the ground-truth bridge before evaluating AI output.",
        ),
        "EV uses the greater of 0.01 absolute currency units and 0.000001 relative error unless overridden by a non-negative fixture value.",
        (
            "The ground-truth capital bridge does not reconcile.",
            "AI enterprise value omits a declared bridge component or exceeds tolerance.",
        ),
        (
            "equation_deviation_delta",
            "omitted_bridge_components",
            "detected_anomalies",
            "rigor_score",
        ),
        "Share-count selection, deal-term extraction, FX normalization, additional debt-like adjustments, and transaction-multiple period tests require provenance-aware ingestion or a future schema extension.",
        ("Investment-Banking-Deal-Validator",),
    ),
)


def get_kernel_spec(module_id: int) -> KernelSpecification:
    """Return one specification by canonical module ID."""
    for specification in KERNEL_SPECIFICATIONS:
        if specification.module_id == module_id:
            return specification
    raise KeyError(f"Unknown AlphaGuard module ID: {module_id}")


def validate_kernel_spec_catalog() -> tuple[str, ...]:
    """Return all catalog errors without mutating the specification objects."""
    errors: list[str] = []
    manifest_by_id = {spec.module_id: spec for spec in MODULE_SPECS}
    catalog_ids = [spec.module_id for spec in KERNEL_SPECIFICATIONS]
    catalog_codes = [spec.code for spec in KERNEL_SPECIFICATIONS]

    if len(KERNEL_SPECIFICATIONS) != 18:
        errors.append("Kernel specification catalog must contain exactly 18 entries.")
    if len(catalog_ids) != len(set(catalog_ids)):
        errors.append("Kernel specification module IDs must be unique.")
    if len(catalog_codes) != len(set(catalog_codes)):
        errors.append("Kernel specification codes must be unique.")
    if set(catalog_ids) != set(manifest_by_id):
        errors.append("Kernel specification IDs must exactly match the module manifest.")

    required_text_fields = ("problem_statement", "tolerance_policy", "data_boundary")
    required_sequence_fields = (
        "ai_inputs",
        "ground_truth_inputs",
        "deterministic_rules",
        "rejection_conditions",
        "outputs",
    )
    for specification in KERNEL_SPECIFICATIONS:
        manifest_spec = manifest_by_id.get(specification.module_id)
        if manifest_spec and specification.code != manifest_spec.code:
            errors.append(
                f"Module {specification.module_id} code does not match the manifest."
            )
        for field_name in required_text_fields:
            value = getattr(specification, field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"Module {specification.module_id} has an empty {field_name}."
                )
        for field_name in required_sequence_fields:
            value = getattr(specification, field_name)
            if not isinstance(value, tuple) or not value:
                errors.append(
                    f"Module {specification.module_id} has no {field_name}."
                )
            elif any(not isinstance(item, str) or not item.strip() for item in value):
                errors.append(
                    f"Module {specification.module_id} has an invalid {field_name} item."
                )
    return tuple(errors)


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=int, help="Print one module specification.")
    arguments = parser.parse_args()

    errors = validate_kernel_spec_catalog()
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1

    payload = (
        asdict(get_kernel_spec(arguments.module))
        if arguments.module
        else [asdict(specification) for specification in KERNEL_SPECIFICATIONS]
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
