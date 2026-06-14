# -*- coding: utf-8 -*-
"""Evaluate GTM and operating strategy artifacts for empirical grounding."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor

class StrategyGroundingAuditor(BaseAuditor):
    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        
        no_evidence_or_owner = ai_data.get("material_recommendation_lacks_evidence", False)
        if no_evidence_or_owner:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Material recommendation lacks evidence or owner", evidence={})
            
        missing_controls = ai_data.get("missing_unit_economics_or_capacity", False)
        if missing_controls:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Unit economics, capacity, or downside mitigation is absent", evidence={})
            
        promotional = ai_data.get("promotional_language_substitutes_action", False)
        if promotional:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Promotional language substitutes for measurable actions", evidence={})
            
        return self.build_scorecard(rigor_score=5.0, approved=True, feedback="Strategy empirically grounded", evidence={
            "unsupported_claims": 0,
            "missing_operating_controls": 0,
            "actionability_ratio": 1.0,
            "strategy_readiness_status": "READY"
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
    print(json.dumps(StrategyGroundingAuditor().execute_audit(ai_out, gt), indent=2))
