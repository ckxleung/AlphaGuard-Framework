# -*- coding: utf-8 -*-
"""One-command AlphaGuard pipeline entry point."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor
from src.market_clock import generate_institutional_timestamp_matrix
from src.module_manifest import MODULE_SPECS
from src.repository_validator import validate_repository
from src.telemetry_router import route_ticker


BANNER = "🛡️ ALPHAGUARD FRAMEWORK: AUTOMATED DAILY AUDIT PIPELINE RUN"
DIVIDER = "=" * 75


def _kernel_identifier(code: str) -> str:
    for specification in MODULE_SPECS:
        if specification.code == code:
            return f"Module_{specification.module_id:02d}_{code}"
    raise KeyError(f"Unknown AlphaGuard module code: {code}")


def _load_json_object(path: Path) -> dict[str, Any]:  # pragma: no cover
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _load_auditor(implementation_path: str, class_name: str) -> BaseAuditor:
    path = ROOT / implementation_path
    spec = importlib.util.spec_from_file_location(
        f"alphaguard_runtime_{path.stem}",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load auditor module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    auditor_class = getattr(module, class_name)
    if not issubclass(auditor_class, BaseAuditor):
        raise TypeError(f"{class_name} must inherit from BaseAuditor.")
    return auditor_class()


def run_pipeline(
    ai_output: dict[str, Any],
    ground_truth: dict[str, Any],
    selected_codes: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Execute selected implemented kernels against one shared payload."""
    validation = validate_repository()
    if not validation["valid"]:
        raise RuntimeError("Repository validation failed before pipeline execution.")

    requested_codes = None if selected_codes is None else set(selected_codes)
    known_codes = {specification.code for specification in MODULE_SPECS}
    if requested_codes is not None:
        unknown_codes = requested_codes.difference(known_codes)
        if unknown_codes:
            raise ValueError(
                "Unknown selected module code(s): "
                + ", ".join(sorted(unknown_codes))
            )

    results: dict[str, Any] = {}
    for specification in MODULE_SPECS:
        if specification.status != "IMPLEMENTED":
            continue
        if requested_codes is not None and specification.code not in requested_codes:
            continue
        auditor = _load_auditor(
            specification.implementation_path,
            specification.class_name,
        )
        scorecard = auditor.execute_audit(dict(ai_output), dict(ground_truth))
        results[specification.code] = BaseAuditor.validate_scorecard(scorecard)

    return {
        "executed_modules": len(results),
        "results": results,
        "repository_status": validation["module_counts"],
    }


def run_module_payloads(
    module_payloads: dict[str, Any],
    *,
    selected_codes: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Execute each selected kernel with its own immutable input payload."""
    if not isinstance(module_payloads, dict):
        raise TypeError("module_payloads must be an object keyed by module code.")
    validation = validate_repository()
    if not validation["valid"]:
        raise RuntimeError("Repository validation failed before pipeline execution.")

    specifications = {specification.code: specification for specification in MODULE_SPECS}
    requested_codes = (
        tuple(module_payloads)
        if selected_codes is None
        else tuple(selected_codes)
    )
    if len(requested_codes) != len(set(requested_codes)):
        raise ValueError("selected_codes cannot contain duplicates.")

    results: dict[str, Any] = {}
    for code in requested_codes:
        specification = specifications.get(code)
        if specification is None:
            raise ValueError(f"Unknown selected module code: {code}")
        if specification.status != "IMPLEMENTED":
            continue
        payload = module_payloads.get(code)
        if payload is None:
            continue
        if not isinstance(payload, dict):
            raise TypeError(f"module_payloads.{code} must be an object.")
        ai_output = payload.get("ai_output")
        ground_truth = payload.get("ground_truth")
        if not isinstance(ai_output, dict) or not isinstance(ground_truth, dict):
            raise TypeError(
                f"module_payloads.{code} must contain ai_output and ground_truth objects."
            )

        auditor = _load_auditor(
            specification.implementation_path,
            specification.class_name,
        )
        scorecard = auditor.execute_audit(dict(ai_output), dict(ground_truth))
        results[code] = BaseAuditor.validate_scorecard(scorecard)

    return {
        "executed_modules": len(results),
        "results": results,
        "repository_status": validation["module_counts"],
    }


def _daily_smoke_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    average_demand = 100.0
    average_lead_time = 10.0
    demand_std = 20.0
    lead_time_std = 2.0
    z_score = 1.65
    safety_stock = z_score * math.sqrt(
        average_lead_time * demand_std**2
        + average_demand**2 * lead_time_std**2
    )
    reorder_point = average_demand * average_lead_time + safety_stock
    settlement_date = date(2026, 1, 1)
    fixed_income_cash_flows = (
        (date(2026, 7, 2), 3.0),
        (date(2027, 1, 1), 103.0),
    )
    yield_to_maturity = 0.05
    coupon_frequency = 2
    present_values = tuple(
        (
            (payment_date - settlement_date).days / 365.0,
            amount
            / math.pow(
                1.0 + yield_to_maturity / coupon_frequency,
                coupon_frequency
                * ((payment_date - settlement_date).days / 365.0),
            ),
        )
        for payment_date, amount in fixed_income_cash_flows
    )
    dirty_price = sum(value for _, value in present_values)
    macaulay_duration = (
        sum(years * value for years, value in present_values) / dirty_price
    )
    modified_duration = macaulay_duration / (
        1.0 + yield_to_maturity / coupon_frequency
    )
    dv01 = modified_duration * dirty_price * 0.0001
    forecast_free_cash_flows = [100.0, 110.0, 121.0]
    wacc = 0.10
    terminal_growth_rate = 0.03
    present_value_cash_flows = sum(
        cash_flow / math.pow(1.0 + wacc, year)
        for year, cash_flow in enumerate(forecast_free_cash_flows, start=1)
    )
    terminal_value = forecast_free_cash_flows[-1] * (
        1.0 + terminal_growth_rate
    ) / (wacc - terminal_growth_rate)
    discounted_terminal_value = terminal_value / math.pow(
        1.0 + wacc,
        len(forecast_free_cash_flows),
    )
    cvib_enterprise_value = present_value_cash_flows + discounted_terminal_value
    cvib_net_debt = 50.0
    cvib_diluted_shares = 10.0
    cvib_equity_value = cvib_enterprise_value - cvib_net_debt
    cvib_price_per_share = cvib_equity_value / cvib_diluted_shares
    generated_api_code = '''
import time
import requests

API_VERSION = "2026-06-01"

def run_client(api_key, user_input):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-API-Version": API_VERSION,
    }
    payload = {"model": "gpt-5.4", "input": user_input}
    for attempt in range(3):
        try:
            response = requests.post(
                "https://api.vendor.example/v1/responses",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if response.status_code == 429:
                time.sleep(int(response.headers.get("Retry-After", "1")))
                continue
            response.raise_for_status()
            return response.json()["output_text"]
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(1)
'''
    filing_text = (
        "Note 7 Revenue Recognition says remaining performance obligations "
        "were $42.0 million. Later, Note 12 Debt says convertible debt "
        "principal was $125.5 million."
    )
    ai_output = {
        "generated_code": generated_api_code,
        "declared_api_version": "2026-06-01",
        "execution_trace": [
            {
                "step_id": "extract",
                "tool_name": "extract_filing",
                "status": "SUCCESS",
                "output": {"filing_id": "10-K-001"},
            },
            {
                "step_id": "search",
                "tool_name": "search_filings",
                "status": "SUCCESS",
                "output": {"matches": ["note-7"]},
            },
            {
                "step_id": "calculate",
                "tool_name": "calculate_metric",
                "status": "SUCCESS",
                "output": {"metric_value": 42.0004},
            },
        ],
        "ai_answers": [
            {
                "question_id": "Q1",
                "answer_text": (
                    "Remaining performance obligations were $42.0 million."
                ),
                "numeric_answer": 42.0,
                "unit": "USD_MILLIONS",
                "cited_span_ids": ["S1"],
                "cited_cell_ids": ["T7.RPO"],
            },
            {
                "question_id": "Q2",
                "answer_text": (
                    "Convertible debt principal was $125.5 million."
                ),
                "numeric_answer": 125.5,
                "unit": "USD_MILLIONS",
                "cited_span_ids": ["S2"],
                "cited_cell_ids": ["T12.DEBT"],
            },
        ],
        "cited_evidence_spans": [
            {
                "span_id": "S1",
                "footnote_id": "N7",
                "source_coordinate": "p84:note7:table1:r2:c3",
                "start_char": 0,
                "end_char": 82,
                "text": (
                    "Note 7 Revenue Recognition says remaining performance "
                    "obligations were $42.0 million."
                ),
            },
            {
                "span_id": "S2",
                "footnote_id": "N12",
                "source_coordinate": "p103:note12:table2:r5:c2",
                "start_char": 86,
                "end_char": 157,
                "text": (
                    "Note 12 Debt says convertible debt principal was "
                    "$125.5 million."
                ),
            },
        ],
        "revenue_forecast": [400.0, 450.0, 500.0, 550.0, 600.0],
        "investment_thesis": "NVDA demand remains supported by disclosed capacity expansion.",
        "reported_operating_cash_flow": 5_080_000_000,
        "calculated_enterprise_value": 168_000_000_000,
        "ai_enterprise_value": cvib_enterprise_value,
        "ai_equity_value": cvib_equity_value,
        "ai_price_per_share": cvib_price_per_share,
        "currency": "USD",
        "valuation_date": "2026-06-12",
        "share_count_basis": "DILUTED_WEIGHTED_AVERAGE",
        "terminal_value_method": "GORDON_GROWTH",
        "ai_multiples": {
            "EV_REVENUE_FY1": 4.0,
            "P_E_FY1": 8.0,
        },
        "ai_reconciliation": {
            "is_balanced": True,
            "total_debits": "1250.00",
            "total_credits": "1250.00",
            "unreconciled_accounts": [],
        },
        "proposed_adjustments": [
            {
                "adjustment_id": "ADJ-001",
                "entries": [
                    {
                        "entity": "ALPHA_US",
                        "account": "6100_EXPENSE",
                        "debit": "10.00",
                        "credit": "0.00",
                        "currency": "USD",
                        "period_end": "2026-03-31",
                        "source_row_ids": ["L3"],
                    },
                    {
                        "entity": "ALPHA_US",
                        "account": "2000_PAYABLES",
                        "debit": "0.00",
                        "credit": "10.00",
                        "currency": "USD",
                        "period_end": "2026-03-31",
                        "source_row_ids": ["L4"],
                    },
                ],
            }
        ],
        "control_narrative": (
            "Ledger rows reconcile to the trial balance; proposed adjustments "
            "are balanced and source-row traced."
        ),
        "sentiment_changes": [0.1, 0.2, 0.3, 0.4],
        "rating": "Buy",
        "reorder_point": reorder_point,
        "safety_stock": safety_stock,
        "methodology": "Dual-variance stochastic safety-stock equation.",
        "ai_price": dirty_price,
        "ai_modified_duration": modified_duration,
        "ai_dv01": dv01,
        "trade_thesis": "RATES_UP_PRICE_DOWN",
        "price_basis": "DIRTY",
        "day_count_convention": "ACT/365F",
        "coupon_frequency": coupon_frequency,
    }
    ground_truth = {
        "filing_text": filing_text,
        "footnote_boundaries": [
            {
                "footnote_id": "N7",
                "title": "Revenue Recognition",
                "start_char": 0,
                "end_char": 82,
                "position_bucket": "middle",
            },
            {
                "footnote_id": "N12",
                "title": "Debt",
                "start_char": 86,
                "end_char": 157,
                "position_bucket": "end",
            },
        ],
        "table_cells": [
            {
                "cell_id": "T7.RPO",
                "footnote_id": "N7",
                "label": "Remaining performance obligations",
                "value": 42.0,
                "unit": "USD_MILLIONS",
                "source_coordinate": "p84:note7:table1:r2:c3",
                "position_bucket": "middle",
            },
            {
                "cell_id": "T12.DEBT",
                "footnote_id": "N12",
                "label": "Convertible debt principal",
                "value": 125.5,
                "unit": "USD_MILLIONS",
                "source_coordinate": "p103:note12:table2:r5:c2",
                "position_bucket": "end",
            },
        ],
        "cross_reference_graph": [
            {
                "question_id": "Q1",
                "required_footnote_ids": ["N7"],
                "required_cell_ids": ["T7.RPO"],
            },
            {
                "question_id": "Q2",
                "required_footnote_ids": ["N12"],
                "required_cell_ids": ["T12.DEBT"],
            },
        ],
        "benchmark_questions": [
            {
                "question_id": "Q1",
                "prompt": "What were remaining performance obligations?",
                "expected_numeric_answer": 42.0,
                "expected_unit": "USD_MILLIONS",
                "numeric_tolerance": 0.01,
                "position_bucket": "middle",
            },
            {
                "question_id": "Q2",
                "prompt": "What was convertible debt principal?",
                "expected_numeric_answer": 125.5,
                "expected_unit": "USD_MILLIONS",
                "numeric_tolerance": 0.01,
                "position_bucket": "end",
            },
        ],
        "filing_id": "SYNTH-10K-2026",
        "api_schema": {
            "api_version": "2026-06-01",
            "endpoint": "/v1/responses",
            "method": "POST",
            "required_payload_fields": ["model", "input"],
            "required_response_fields": ["output_text"],
        },
        "breaking_change_manifest": {
            "deprecated_versions": ["2025-01-01"],
            "removed_endpoints": ["/v1/completions"],
        },
        "required_headers": [
            "Authorization",
            "Content-Type",
            "X-API-Version",
        ],
        "rate_limit_policy": {
            "requires_429_retry": True,
            "retry_after_header": "Retry-After",
            "min_retry_attempts": 3,
        },
        "mandatory_tool_steps": [
            {
                "step_id": "extract",
                "tool_name": "extract_filing",
                "required_output_keys": ["filing_id"],
            },
            {
                "step_id": "search",
                "tool_name": "search_filings",
                "required_output_keys": ["matches"],
            },
            {
                "step_id": "calculate",
                "tool_name": "calculate_metric",
                "required_output_keys": ["metric_value"],
                "expected_numeric_output": 42.0,
                "numeric_tolerance": 0.001,
            },
        ],
        "current_capacity": 100.0,
        "capex_additions": [10.0, 10.0, 10.0, 10.0, 10.0],
        "capital_efficiency": 2.0,
        "max_utilization": 0.90,
        "blended_asp": 5.0,
        "net_income": 5_000_000_000,
        "non_cash_adjustments": 600_000_000,
        "increase_in_net_working_capital": 520_000_000,
        "reported_operating_cash_flow": 5_080_000_000,
        "currency": "USD",
        "source_id": "DOC-SYNTHETIC-ALPHAGUARD-001",
        "fiscal_period_end": "2026-03-31",
        "equity_value": 150_000_000_000,
        "total_debt": 25_000_000_000,
        "cash_and_equivalents": 12_000_000_000,
        "preferred_stock": 500_000_000,
        "non_controlling_interests": 4_500_000_000,
        "reported_enterprise_value": 168_000_000_000,
        "equity_value_basis": "SYNTHETIC_MARKET_CAPITALIZATION",
        "valuation_date": "2026-06-12",
        "forecast_free_cash_flows": forecast_free_cash_flows,
        "wacc": wacc,
        "terminal_growth_rate": terminal_growth_rate,
        "net_debt": cvib_net_debt,
        "diluted_shares": cvib_diluted_shares,
        "share_count_basis": "DILUTED_WEIGHTED_AVERAGE",
        "comparable_company_metrics": [
            {
                "metric_name": "EV_REVENUE_FY1",
                "numerator_basis": "ENTERPRISE_VALUE",
                "numerator": 1000.0,
                "denominator": 250.0,
                "denominator_period": "FY1_FORWARD",
            },
            {
                "metric_name": "P_E_FY1",
                "numerator_basis": "EQUITY_VALUE",
                "numerator": 800.0,
                "denominator": 100.0,
                "denominator_period": "FY1_FORWARD",
            },
        ],
        "ledger_rows": [
            {
                "row_id": "L1",
                "entity": "ALPHA_US",
                "account": "1000_CASH",
                "debit": "1000.00",
                "credit": "0.00",
                "currency": "USD",
                "period_end": "2026-03-31",
            },
            {
                "row_id": "L2",
                "entity": "ALPHA_US",
                "account": "4000_REVENUE",
                "debit": "0.00",
                "credit": "1000.00",
                "currency": "USD",
                "period_end": "2026-03-31",
            },
            {
                "row_id": "L3",
                "entity": "ALPHA_US",
                "account": "6100_EXPENSE",
                "debit": "250.00",
                "credit": "0.00",
                "currency": "USD",
                "period_end": "2026-03-31",
            },
            {
                "row_id": "L4",
                "entity": "ALPHA_US",
                "account": "2000_PAYABLES",
                "debit": "0.00",
                "credit": "250.00",
                "currency": "USD",
                "period_end": "2026-03-31",
            },
        ],
        "trial_balance": [
            {
                "entity": "ALPHA_US",
                "account": "1000_CASH",
                "debit": "1000.00",
                "credit": "0.00",
                "currency": "USD",
                "period_end": "2026-03-31",
            },
            {
                "entity": "ALPHA_US",
                "account": "4000_REVENUE",
                "debit": "0.00",
                "credit": "1000.00",
                "currency": "USD",
                "period_end": "2026-03-31",
            },
            {
                "entity": "ALPHA_US",
                "account": "6100_EXPENSE",
                "debit": "250.00",
                "credit": "0.00",
                "currency": "USD",
                "period_end": "2026-03-31",
            },
            {
                "entity": "ALPHA_US",
                "account": "2000_PAYABLES",
                "debit": "0.00",
                "credit": "250.00",
                "currency": "USD",
                "period_end": "2026-03-31",
            },
        ],
        "account_mapping": {
            "1000_CASH": "ASSET",
            "4000_REVENUE": "REVENUE",
            "6100_EXPENSE": "EXPENSE",
            "2000_PAYABLES": "LIABILITY",
        },
        "period_end": "2026-03-31",
        "block_trades_outflow": [-5.0, -8.0, -10.0, -12.0],
        "retail_orderflow_imbalance": [2.0, 3.0, 4.0, 5.0],
        "discussion_volume": [100.0, 110.0, 120.0, 130.0],
        "price_changes": [0.01, 0.02, 0.02, 0.03],
        "average_demand": average_demand,
        "average_lead_time": average_lead_time,
        "demand_std": demand_std,
        "lead_time_std": lead_time_std,
        "service_level": 0.95,
        "cash_flow_schedule": [
            {
                "payment_date": payment_date.isoformat(),
                "amount": amount,
            }
            for payment_date, amount in fixed_income_cash_flows
        ],
        "yield_to_maturity": yield_to_maturity,
        "settlement_date": settlement_date.isoformat(),
        "day_count_convention": "ACT/365F",
        "coupon_frequency": coupon_frequency,
        "face_value": 100.0,
        "price_basis": "DIRTY",
        "accrued_interest": 0.0,
    }
    return ai_output, ground_truth


def run_daily_smoke(
    ticker: str = "NVDA",
    market_event: str | None = None,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    route = route_ticker(ticker, market_event=market_event)
    ai_output, ground_truth = _daily_smoke_inputs()
    route_codes = tuple(
        kernel.replace("Module_", "").split("_", 1)[1]
        for kernel in route["triggered_kernels"]
    )
    pipeline_report = run_pipeline(
        ai_output,
        ground_truth,
        selected_codes=route_codes,
    )
    timestamp_matrix = generate_institutional_timestamp_matrix(observed_at)

    scorecards = []
    unavailable_kernels = []
    for code in route_codes:
        result = pipeline_report["results"].get(code)
        if result is None:
            unavailable_kernels.append(_kernel_identifier(code))
            continue
        scorecard = dict(result)
        scorecard.update(
            {
                "kernel_id": _kernel_identifier(code),
                "detected_anomalies": []
                if scorecard.get("data_quality_status") == "APPROVED"
                else [scorecard.get("structured_written_feedback", "Rejected by kernel.")],
            }
        )
        scorecards.append(scorecard)

    return {
        "telemetry_timestamp_matrix": timestamp_matrix,
        "data_provenance": {
            "synthetic_data": True,
            "source_id": "DOC-SYNTHETIC-ALPHAGUARD-001",
            "publication_eligible": False,
        },
        "routing_specs": route,
        "forensic_audit_scorecard": scorecards,
        "unavailable_kernels": unavailable_kernels,
        "repository_status": pipeline_report["repository_status"],
        "substack_ready_flag": False,
    }


def print_daily_smoke_report(
    ticker: str = "NVDA",
    market_event: str | None = None,
) -> None:
    observed_at = datetime.now(timezone.utc)
    route = route_ticker(ticker, market_event=market_event)
    utc_log_time = observed_at.isoformat(timespec="seconds").replace("+00:00", "Z")
    print(DIVIDER)
    print(BANNER)
    print(DIVIDER)
    print(
        f"{utc_log_time} [INFO] "
        f"(AlphaGuard-Router) Successfully routed {route['ticker']} to "
        f"{route['target_infrastructure_layer']} with priority "
        f"[{route['priority_level']}]"
    )
    print(
        f"{utc_log_time} [INFO] "
        f"(AlphaGuard-Pipeline) Ingesting market data vectors for {route['ticker']}..."
    )
    print(
        json.dumps(
            run_daily_smoke(
                ticker,
                market_event=market_event,
                observed_at=observed_at,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )
    print(DIVIDER)


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-output", type=Path)
    parser.add_argument("--ground-truth", type=Path)
    parser.add_argument("--ticker", default="NVDA")
    parser.add_argument("--event", dest="market_event")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the repository without executing kernels.",
    )
    arguments = parser.parse_args()

    if arguments.validate_only:
        report = validate_repository()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["valid"] else 1

    if not arguments.ai_output or not arguments.ground_truth:
        print_daily_smoke_report(arguments.ticker, market_event=arguments.market_event)
        return 0

    report = run_pipeline(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
