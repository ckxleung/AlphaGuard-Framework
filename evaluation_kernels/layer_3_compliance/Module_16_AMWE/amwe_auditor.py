# -*- coding: utf-8 -*-
"""Detect temporal leakage and invalid validation splits."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor

class AppliedMLWorkflowAuditor(BaseAuditor):
    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        
        leakage = ai_data.get("future_information_in_feature", False)
        if leakage:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Feature uses future observations", evidence={})
            
        invalid_split = ai_data.get("random_kfold_on_time_dependent_rows", False)
        if invalid_split:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Random K-fold used on time-dependent rows", evidence={})
            
        misleading_metric = ai_data.get("accuracy_sole_metric_for_imbalanced", False)
        if misleading_metric:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Accuracy is sole metric for imbalanced target", evidence={})
            
        return self.build_scorecard(rigor_score=5.0, approved=True, feedback="ML workflow verified", evidence={
            "leakage_events": 0,
            "split_integrity_status": "VALID",
            "metric_alignment_status": "ALIGNED",
            "technical_quality_score": 100.0
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
    print(json.dumps(AppliedMLWorkflowAuditor().execute_audit(ai_out, gt), indent=2))
