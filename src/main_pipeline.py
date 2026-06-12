# -*- coding: utf-8 -*-
"""One-command AlphaGuard pipeline entry point."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
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
) -> dict[str, Any]:
    """Execute every implemented kernel and validate every scorecard."""
    validation = validate_repository()
    if not validation["valid"]:
        raise RuntimeError("Repository validation failed before pipeline execution.")

    results: dict[str, Any] = {}
    for specification in MODULE_SPECS:
        if specification.status != "IMPLEMENTED":
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
    ai_output = {
        "revenue_forecast": [400.0, 450.0, 500.0, 550.0, 600.0],
        "investment_thesis": "NVDA demand remains supported by disclosed capacity expansion.",
        "reported_operating_cash_flow": 5_080_000_000,
        "sentiment_changes": [0.1, 0.2, 0.3, 0.4],
        "rating": "Buy",
        "reorder_point": reorder_point,
        "safety_stock": safety_stock,
        "methodology": "Dual-variance stochastic safety-stock equation.",
    }
    ground_truth = {
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
        "source_id": "SYNTHETIC-DAILY-SMOKE",
        "fiscal_period_end": "2026-03-31",
        "block_trades_outflow": [-5.0, -8.0, -10.0, -12.0],
        "retail_orderflow_imbalance": [2.0, 3.0, 4.0, 5.0],
        "discussion_volume": [100.0, 110.0, 120.0, 130.0],
        "price_changes": [0.01, 0.02, 0.02, 0.03],
        "average_demand": average_demand,
        "average_lead_time": average_lead_time,
        "demand_std": demand_std,
        "lead_time_std": lead_time_std,
        "service_level": 0.95,
    }
    return ai_output, ground_truth


def run_daily_smoke(
    ticker: str = "NVDA",
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    route = route_ticker(ticker)
    ai_output, ground_truth = _daily_smoke_inputs()
    pipeline_report = run_pipeline(ai_output, ground_truth)
    timestamp_matrix = generate_institutional_timestamp_matrix(observed_at)

    route_codes = {
        kernel.replace("Module_", "").split("_", 1)[1]
        for kernel in route["triggered_kernels"]
    }
    scorecards = []
    unavailable_kernels = []
    for code in sorted(route_codes):
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
            "source_id": "SYNTHETIC-DAILY-SMOKE",
            "publication_eligible": False,
        },
        "routing_specs": route,
        "forensic_audit_scorecard": scorecards,
        "unavailable_kernels": unavailable_kernels,
        "repository_status": pipeline_report["repository_status"],
        "substack_ready_flag": False,
    }


def print_daily_smoke_report(ticker: str = "NVDA") -> None:
    observed_at = datetime.now(timezone.utc)
    route = route_ticker(ticker)
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
            run_daily_smoke(ticker, observed_at=observed_at),
            indent=2,
            ensure_ascii=False,
        )
    )
    print(DIVIDER)


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-output", type=Path)
    parser.add_argument("--ground-truth", type=Path)
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
        print_daily_smoke_report("NVDA")
        return 0

    report = run_pipeline(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
