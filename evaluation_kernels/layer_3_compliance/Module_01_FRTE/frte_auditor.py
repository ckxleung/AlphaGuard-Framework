# -*- coding: utf-8 -*-
"""Audit newly introduced filing risks that an AI summary omits or invents."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor


class FilingRiskDeltaAuditor(BaseAuditor):
    """Detect omitted or invented risk disclosures in filing summaries."""

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)

        ai_summary = ai_data.get("ai_summary", "")
        claimed_risk_deltas = ai_data.get("claimed_risk_deltas", [])

        prior_text = truth.get("prior_period_filing_text", "")
        current_text = truth.get("current_period_filing_text", "")
        section_boundaries = truth.get("section_boundaries", [])
        materiality_rubric = truth.get("materiality_rubric", {})
        source_ids = truth.get("source_ids", [])
        period_end_dates = truth.get("period_end_dates", [])

        if not isinstance(prior_text, str) or not isinstance(current_text, str):
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Filing text must be strings.", evidence={})
        if not isinstance(section_boundaries, list) or not isinstance(source_ids, list) or not isinstance(period_end_dates, list):
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Invalid ground truth list inputs.", evidence={})
        if not isinstance(claimed_risk_deltas, list):
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="claimed_risk_deltas must be a list.", evidence={})

        if len(period_end_dates) != 2:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Must provide exactly two period end dates for comparison.", evidence={})

        # Rule 3: Periods, filing sections, or provenance are not comparable.
        truth_comparable = truth.get("are_filings_comparable", True)
        if not truth_comparable:
            return self.build_scorecard(rigor_score=0.0, approved=False, feedback="Periods, filing sections, or provenance are not comparable.", evidence={})

        material_delta_count = truth.get("material_delta_count", len(section_boundaries))
        omitted_material_deltas = []
        unsupported_ai_claims = []

        truth_deltas = truth.get("actual_material_deltas", [])

        # Rule 1: A material new risk delta has no supported AI-summary coverage
        for expected_delta in truth_deltas:
            found = False
            for claim in claimed_risk_deltas:
                if claim.get("topic") == expected_delta.get("topic"):
                    found = True
                    break
            if not found:
                omitted_material_deltas.append(expected_delta)

        # Rule 2: The AI summary asserts a risk change absent from the current-versus-prior filing delta.
        for claim in claimed_risk_deltas:
            found = False
            for expected_delta in truth_deltas:
                if expected_delta.get("topic") == claim.get("topic"):
                    found = True
                    break
            if not found:
                unsupported_ai_claims.append(claim)

        if omitted_material_deltas:
            return self._build_scorecard(
                "Module_01_FRTE",
                "REJECTED",
                1.0,
                f"Omitted {len(omitted_material_deltas)} material risk deltas.",
                {
                    "omitted_material_deltas": omitted_material_deltas,
                    "unsupported_ai_claims": unsupported_ai_claims
                }
            )

        if unsupported_ai_claims:
            return self._build_scorecard(
                "Module_01_FRTE",
                "REJECTED",
                1.0,
                f"AI invented {len(unsupported_ai_claims)} risk changes not in the delta.",
                {
                    "omitted_material_deltas": omitted_material_deltas,
                    "unsupported_ai_claims": unsupported_ai_claims
                }
            )

        coverage_ratio = 1.0 if material_delta_count == 0 else (material_delta_count - len(omitted_material_deltas)) / material_delta_count

        return self.build_scorecard(rigor_score=5.0, approved=True, feedback="All material risk deltas correctly identified with no inventions.", evidence={
                "material_delta_count": material_delta_count,
                "omitted_material_deltas": omitted_material_deltas,
                "unsupported_ai_claims": unsupported_ai_claims,
                "coverage_ratio": coverage_ratio
            })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FilingRiskDeltaAuditor")
    parser.add_argument("--ai-output", required=True, type=Path)
    parser.add_argument("--ground-truth", required=True, type=Path)
    args = parser.parse_args()

    with open(args.ai_output, "r", encoding="utf-8") as f:
        ai_out = json.load(f)
    with open(args.ground_truth, "r", encoding="utf-8") as f:
        gt = json.load(f)

    auditor = FilingRiskDeltaAuditor()
    print(json.dumps(auditor.execute_audit(ai_out, gt), indent=2))
