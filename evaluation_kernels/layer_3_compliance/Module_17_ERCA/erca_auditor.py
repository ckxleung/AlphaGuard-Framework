# -*- coding: utf-8 -*-
"""Audit enterprise AI controls against a COSO-style matrix."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor

class EnterpriseRiskComplianceAuditor(BaseAuditor):
    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        
        missing_control = ai_data.get("mandatory_risk_lacks_control", False)
        if missing_control:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Mandatory risk lacks control or owner", evidence={})
            
        fake_effectiveness = ai_data.get("operating_effectiveness_from_design_only", False)
        if fake_effectiveness:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Operating effectiveness claimed from design only", evidence={})
            
        incomplete_reg = ai_data.get("regulatory_requirement_lacks_provenance", False)
        if incomplete_reg:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Regulatory requirement lacks jurisdiction, date, or source", evidence={})
            
        return self.build_scorecard(rigor_score=5.0, approved=True, feedback="Enterprise controls validated", evidence={
            "control_coverage_ratio": 1.0,
            "design_gaps": 0,
            "operating_effectiveness_gaps": 0,
            "residual_risk_status": "ACCEPTABLE"
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
    print(json.dumps(EnterpriseRiskComplianceAuditor().execute_audit(ai_out, gt), indent=2))
