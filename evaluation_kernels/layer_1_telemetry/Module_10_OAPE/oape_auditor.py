# -*- coding: utf-8 -*-
"""Audit Office Artifact Pair Evaluation (OAPE)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor


class OfficeArtifactAuditor(BaseAuditor):
    """Deterministic pairwise evaluation for XLSX, DOCX, and PPTX artifacts."""

    @staticmethod
    def _bool(payload: Mapping[str, Any], key: str) -> bool:
        value = payload.get(key)
        if not isinstance(value, bool):
            raise TypeError(f"{key} must be a boolean.")
        return value

    @staticmethod
    def _float(payload: Mapping[str, Any], key: str) -> float:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{key} must be numeric.")
        return float(value)

    @staticmethod
    def _string(payload: Mapping[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str):
            raise TypeError(f"{key} must be a string.")
        return value.strip()

    @classmethod
    def _validate_ai_output(cls, payload: Mapping[str, Any]) -> dict[str, Any]:
        winner = cls._string(payload, "winner")
        if winner not in {"candidate_a", "candidate_b", "tie"}:
            raise ValueError("winner must be 'candidate_a', 'candidate_b', or 'tie'.")
        
        return {
            "winner": winner,
            "candidate_a_score": cls._float(payload, "candidate_a_score"),
            "candidate_b_score": cls._float(payload, "candidate_b_score"),
            "visual_overlap_absent": cls._bool(payload, "visual_overlap_absent"),
        }

    @classmethod
    def _validate_candidate_truth(cls, payload: Mapping[str, Any], prefix: str) -> dict[str, bool]:
        cand = payload.get(prefix)
        if not isinstance(cand, Mapping):
            raise TypeError(f"{prefix} must be a dictionary in ground_truth.")
        
        return {
            "broken_formulas": cls._bool(cand, "broken_formulas"),
            "invalid_relationships": cls._bool(cand, "invalid_relationships"),
            "clipping_or_overlap": cls._bool(cand, "clipping_or_overlap"),
            "metadata_only_difference": cls._bool(cand, "metadata_only_difference"),
        }

    @classmethod
    def _validate_ground_truth(cls, payload: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "comparison_settings_equivalent": cls._bool(payload, "comparison_settings_equivalent"),
            "candidate_a": cls._validate_candidate_truth(payload, "candidate_a"),
            "candidate_b": cls._validate_candidate_truth(payload, "candidate_b"),
        }

    def execute_audit(self, ai_output: Dict, ground_truth: Dict) -> Dict:
        """Audit pairwise evaluation of office artifacts."""
        ai_out, truth = self.validate_inputs(ai_output, ground_truth)

        # Parse inputs
        parsed_ai = self._validate_ai_output(ai_out)
        parsed_truth = self._validate_ground_truth(truth)

        # 1. Comparison settings must be equivalent
        if not parsed_truth["comparison_settings_equivalent"]:
            return self.build_scorecard(
                rigor_score=0.0,
                approved=False,
                feedback="Comparison settings are not equivalent. Cannot evaluate.",
            )
        
        # 2. Arbitrary winner selected from equal scores
        if parsed_ai["candidate_a_score"] == parsed_ai["candidate_b_score"] and parsed_ai["winner"] != "tie":
            return self.build_scorecard(
                rigor_score=0.0,
                approved=False,
                feedback="Arbitrary winner selected from equal scores.",
            )
        
        # 3. Metadata alone cannot establish absence of visual overlap
        if parsed_ai["visual_overlap_absent"]:
            cand_a_metadata_only = parsed_truth["candidate_a"]["metadata_only_difference"]
            cand_b_metadata_only = parsed_truth["candidate_b"]["metadata_only_difference"]
            if cand_a_metadata_only or cand_b_metadata_only:
                return self.build_scorecard(
                    rigor_score=1.0,
                    approved=False,
                    feedback="Metadata alone cannot establish absence of visual overlap.",
                )

        # 4. Check for critical defects in the chosen winner
        winner = parsed_ai["winner"]
        if winner in ("candidate_a", "candidate_b"):
            cand_truth = parsed_truth[winner]
            if cand_truth["broken_formulas"] or cand_truth["invalid_relationships"] or cand_truth["clipping_or_overlap"]:
                return self.build_scorecard(
                    rigor_score=2.0,
                    approved=False,
                    feedback=f"Selected winner ({winner}) contains critical defects (broken formulas, invalid relationships, or clipping/overlap).",
                )

        # All checks passed
        return self.build_scorecard(
            rigor_score=5.0,
            approved=True,
            feedback="Pairwise evaluation meets all strict deterministic criteria.",
        )


def _load_json_object(path: Path) -> dict[str, Any]:  # pragma: no cover
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-output", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, required=True)
    arguments = parser.parse_args()
    result = OfficeArtifactAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

