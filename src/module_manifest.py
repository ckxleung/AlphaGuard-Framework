# -*- coding: utf-8 -*-
"""Authoritative, immutable registry for the eighteen AlphaGuard kernels."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class ModuleSpec:
    module_id: int
    code: str
    name: str
    layer: str
    class_name: str
    status: str
    implementation_path: str = ""


MODULE_SPECS: Final[tuple[ModuleSpec, ...]] = (
    ModuleSpec(1, "FRTE", "Financial Risk Text Evolution", "layer_3_compliance", "FinancialRiskTextAuditor", "SPECIFIED"),
    ModuleSpec(2, "APAC", "Asia-Pacific Cross-Market Transmission", "layer_2_valuation", "CrossMarketTransmissionAuditor", "SPECIFIED"),
    ModuleSpec(3, "AMDG", "Asset Management Deliverable Gateway", "layer_4_strategy", "AssetManagementDeliverableAuditor", "SPECIFIED"),
    ModuleSpec(4, "CASS", "Conflict-Aware Agent Sandbox", "layer_4_strategy", "ConflictAwareSandboxAuditor", "SPECIFIED"),
    ModuleSpec(5, "SFRA", "SEC Footnote Reasoning Audit", "layer_1_telemetry", "SecFootnoteReasoningAuditor", "SPECIFIED"),
    ModuleSpec(6, "TLAB", "Technical Latency and API Benchmark", "layer_1_telemetry", "ApiTelemetryAuditor", "IMPLEMENTED", "evaluation_kernels/layer_1_telemetry/Module_06_TLAB/tlab_auditor.py"),
    ModuleSpec(7, "BLSB", "Business-Language Strategy Benchmark", "layer_4_strategy", "BusinessLanguageAuditor", "SPECIFIED"),
    ModuleSpec(8, "FOAS", "Financial Operations Automated Settlement", "layer_3_compliance", "FinancialReconciliationAuditor", "IMPLEMENTED", "evaluation_kernels/layer_3_compliance/Module_08_FOAS/foas_auditor.py"),
    ModuleSpec(9, "FITV", "Fixed-Income Term-Structure Validation", "layer_2_valuation", "FixedIncomeAuditor", "IMPLEMENTED", "evaluation_kernels/layer_2_valuation/Module_09_FITV/fitv_auditor.py"),
    ModuleSpec(10, "OAPE", "Office Artifact Pair Evaluation", "layer_1_telemetry", "OfficeArtifactAuditor", "SPECIFIED"),
    ModuleSpec(11, "CVIB", "Core Valuation Integrity Benchmark", "layer_2_valuation", "CoreValuationAuditor", "IMPLEMENTED", "evaluation_kernels/layer_2_valuation/Module_11_CVIB/cvib_auditor.py"),
    ModuleSpec(12, "IRTA", "Buy-Side Institutional Research Thesis Audit", "layer_4_strategy", "InstitutionalResearchThesisAuditor", "IMPLEMENTED", "evaluation_kernels/layer_4_strategy/Module_12_IRTA/institutional_research_thesis_auditor.py"),
    ModuleSpec(13, "BMAE", "Behavioral Market-Microstructure Alpha Engine", "layer_4_strategy", "BehavioralMarketAuditor", "IMPLEMENTED", "evaluation_kernels/layer_4_strategy/Module_13_BMAE/behavioral_market_auditor.py"),
    ModuleSpec(14, "CFIA", "Corporate Financial Integrity Audit", "layer_2_valuation", "CorporateFinancialAuditor", "IMPLEMENTED", "evaluation_kernels/layer_2_valuation/Module_14_CFIA/cfia_auditor.py"),
    ModuleSpec(15, "SCGV", "Supply Chain GenAI Validator", "layer_4_strategy", "SupplyChainAuditor", "IMPLEMENTED", "evaluation_kernels/layer_4_strategy/Module_15_SCGV/supply_chain_auditor.py"),
    ModuleSpec(16, "AMWE", "AI Model Walk-Forward Evaluation", "layer_3_compliance", "TimeSeriesLeakageAuditor", "SPECIFIED"),
    ModuleSpec(17, "ERCA", "Enterprise Risk and Compliance Audit", "layer_3_compliance", "EnterpriseComplianceAuditor", "SPECIFIED"),
    ModuleSpec(18, "IBDV", "Investment-Banking Deal Validation", "layer_2_valuation", "InvestmentBankingDealAuditor", "IMPLEMENTED", "evaluation_kernels/layer_2_valuation/Module_18_IBDV/ibdv_auditor.py"),
)


def get_module_spec(module_id: int) -> ModuleSpec:
    """Return one module specification or fail closed."""
    for specification in MODULE_SPECS:
        if specification.module_id == module_id:
            return specification
    raise KeyError(f"Unknown AlphaGuard module ID: {module_id}")


def validate_manifest() -> tuple[str, ...]:
    """Return validation errors without mutating the registry."""
    errors: list[str] = []
    ids = [spec.module_id for spec in MODULE_SPECS]
    codes = [spec.code for spec in MODULE_SPECS]
    valid_layers = {
        "layer_1_telemetry",
        "layer_2_valuation",
        "layer_3_compliance",
        "layer_4_strategy",
        "UNASSIGNED",
    }

    if len(MODULE_SPECS) != 18:
        errors.append("Manifest must contain exactly 18 modules.")
    if len(ids) != len(set(ids)):
        errors.append("Module IDs must be unique.")
    if set(ids) != set(range(1, 19)):
        errors.append("Module IDs must cover the inclusive range 1..18.")
    if len(codes) != len(set(codes)):
        errors.append("Module codes must be unique.")

    for spec in MODULE_SPECS:
        if spec.layer not in valid_layers:
            errors.append(f"Module {spec.module_id} has an invalid layer.")
        if spec.status == "IMPLEMENTED" and not spec.implementation_path:
            errors.append(
                f"Module {spec.module_id} is IMPLEMENTED without an implementation path."
            )
        if spec.status == "SPEC_REQUIRED" and spec.implementation_path:
            errors.append(
                f"Module {spec.module_id} cannot have code before its specification."
            )
    return tuple(errors)


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=int, help="Print one module by numeric ID.")
    arguments = parser.parse_args()

    errors = validate_manifest()
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1

    payload = (
        asdict(get_module_spec(arguments.module))
        if arguments.module
        else [asdict(spec) for spec in MODULE_SPECS]
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
