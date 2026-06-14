# -*- coding: utf-8 -*-
"""Test whether an AI strategy resolves explicit conflicts among stakeholder constraints."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor

class StrategyConflictAuditor(BaseAuditor):
    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        
        non_negotiable_violation = ai_data.get("non_negotiable_constraint_violated", False)
        if non_negotiable_violation:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="A non-negotiable constraint is violated", evidence={})
            
        fake_consensus = ai_data.get("incompatible_commitments_as_consensus", False)
        if fake_consensus:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Conflicting stakeholder commitments presented as consensus", evidence={})
            
        unresolved_conflict = ai_data.get("material_conflict_lacks_resolution", False)
        if unresolved_conflict:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Material conflict lacks explicit resolution", evidence={})
            
        return self.build_scorecard(rigor_score=5.0, approved=True, feedback="Conflicts resolved", evidence={
            "constraint_violations": 0,
            "unresolved_conflicts": 0,
            "stakeholder_feedback_matrix": [],
            "reconciliation_required": False
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
    print(json.dumps(StrategyConflictAuditor().execute_audit(ai_out, gt), indent=2))
