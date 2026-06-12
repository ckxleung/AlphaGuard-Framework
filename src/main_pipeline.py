# -*- coding: utf-8 -*-
"""One-command AlphaGuard pipeline entry point."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor
from src.module_manifest import MODULE_SPECS
from src.repository_validator import validate_repository
from src.telemetry_router import route_ticker


BANNER = "🛡️ ALPHAGUARD FRAMEWORK: AUTOMATED DAILY AUDIT PIPELINE RUN"
DIVIDER = "=" * 75


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


def run_daily_smoke(ticker: str = "NVDA") -> dict[str, Any]:
    route = route_ticker(ticker)
    ai_output, ground_truth = _daily_smoke_inputs()
    pipeline_report = run_pipeline(ai_output, ground_truth)

    route_codes = {
        kernel.replace("Module_", "").split("_", 1)[1]
        for kernel in route["triggered_kernels"]
    }
    scorecards = []
    for code in sorted(route_codes):
        scorecard = dict(pipeline_report["results"].get(code, {}))
        scorecard.update(
            {
                "kernel_id": f"Module_{next(spec.module_id for spec in MODULE_SPECS if spec.code == code):02d}_{code}",
                "detected_anomalies": []
                if scorecard.get("data_quality_status") == "APPROVED"
                else [scorecard.get("structured_written_feedback", "Rejected by kernel.")],
            }
        )
        scorecards.append(scorecard)

    return {
        "telemetry_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S HKT"),
        "routing_specs": route,
        "forensic_audit_scorecard": scorecards,
        "repository_status": pipeline_report["repository_status"],
        "substack_ready_flag": all(
            item.get("data_quality_status") == "APPROVED" for item in scorecards
        ),
    }


def print_daily_smoke_report(ticker: str = "NVDA") -> None:
    route = route_ticker(ticker)
    print(DIVIDER)
    print(BANNER)
    print(DIVIDER)
    print(
        f"{datetime.now():%Y-%m-%d %H:%M:%S} [INFO] "
        f"(AlphaGuard-Router) Successfully routed {route['ticker']} to "
        f"{route['target_infrastructure_layer']} with priority "
        f"[{route['priority_level']}]"
    )
    print(
        f"{datetime.now():%Y-%m-%d %H:%M:%S} [INFO] "
        f"(AlphaGuard-Pipeline) Ingesting market data vectors for {route['ticker']}..."
    )
    print(json.dumps(run_daily_smoke(ticker), indent=2, ensure_ascii=False))
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
