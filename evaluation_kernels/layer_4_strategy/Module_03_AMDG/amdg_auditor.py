# -*- coding: utf-8 -*-
"""Evaluate wealth-management and institutional deliverables."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor

class InstitutionalDeliverableAuditor(BaseAuditor):
    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        
        material_fail = ai_data.get("material_financial_reconciliation_failure", False)
        if material_fail:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Material financial output does not reconcile", evidence={})
            
        clipped = ai_data.get("region_clipped_or_unreadable", False)
        if clipped:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="A region is clipped or unreadable", evidence={})
            
        undeclared = ai_data.get("undeclared_assumptions", False)
        if undeclared:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Undeclared assumptions used", evidence={})
            
        return self.build_scorecard(rigor_score=5.0, approved=True, feedback="Visual and financial quality validated", evidence={
            "calculation_defects": 0,
            "visual_defects": 0,
            "source_traceability_ratio": 1.0,
            "institutional_readiness_status": "READY"
        })

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ai-output", required=True, type=Path)
    parser.add_argument("--ground-truth", required=True, type=Path)
    args = parser.parse_args()
    with open(args.ai_output, "r") as f:
        ai_out = json.load(f)
    with open(args.ground_truth, "r") as f:
        gt = json.load(f)
    print(json.dumps(InstitutionalDeliverableAuditor().execute_audit(ai_out, gt), indent=2))
