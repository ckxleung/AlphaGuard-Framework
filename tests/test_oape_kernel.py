from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class OfficeArtifactAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        from evaluation_kernels.layer_1_telemetry.Module_10_OAPE.oape_auditor import (
            OfficeArtifactAuditor,
        )

        self.auditor = OfficeArtifactAuditor()
        self.ground_truth = {
            "comparison_settings_equivalent": True,
            "candidate_a": {
                "broken_formulas": False,
                "invalid_relationships": False,
                "clipping_or_overlap": False,
                "metadata_only_difference": False,
            },
            "candidate_b": {
                "broken_formulas": False,
                "invalid_relationships": False,
                "clipping_or_overlap": False,
                "metadata_only_difference": False,
            },
        }

    def valid_ai_output(self) -> dict:
        return {
            "winner": "candidate_a",
            "candidate_a_score": 85.0,
            "candidate_b_score": 72.0,
            "visual_overlap_absent": False,
        }

    # ---- Approval Tests ----

    def test_approves_valid_winner_selection(self) -> None:
        scorecard = self.auditor.execute_audit(
            self.valid_ai_output(),
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)

    def test_approves_valid_tie(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["winner"] = "tie"
        ai_output["candidate_a_score"] = 80.0
        ai_output["candidate_b_score"] = 80.0

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)

    def test_approves_candidate_b_winner(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["winner"] = "candidate_b"
        ai_output["candidate_a_score"] = 60.0
        ai_output["candidate_b_score"] = 90.0

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)

    def test_approves_visual_overlap_absent_when_no_metadata_only_diff(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["visual_overlap_absent"] = True

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")

    # ---- Rejection Tests ----

    def test_rejects_non_equivalent_comparison_settings(self) -> None:
        truth = copy.deepcopy(self.ground_truth)
        truth["comparison_settings_equivalent"] = False

        scorecard = self.auditor.execute_audit(self.valid_ai_output(), truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 0.0)
        self.assertIn("not equivalent", scorecard["structured_written_feedback"])

    def test_rejects_arbitrary_winner_from_equal_scores(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["candidate_a_score"] = 80.0
        ai_output["candidate_b_score"] = 80.0
        ai_output["winner"] = "candidate_a"

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 0.0)
        self.assertIn("Arbitrary winner", scorecard["structured_written_feedback"])

    def test_rejects_winner_with_broken_formulas(self) -> None:
        truth = copy.deepcopy(self.ground_truth)
        truth["candidate_a"]["broken_formulas"] = True

        scorecard = self.auditor.execute_audit(self.valid_ai_output(), truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 2.0)
        self.assertIn("critical defects", scorecard["structured_written_feedback"])

    def test_rejects_winner_with_invalid_relationships(self) -> None:
        truth = copy.deepcopy(self.ground_truth)
        truth["candidate_a"]["invalid_relationships"] = True

        scorecard = self.auditor.execute_audit(self.valid_ai_output(), truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 2.0)

    def test_rejects_winner_with_clipping_or_overlap(self) -> None:
        truth = copy.deepcopy(self.ground_truth)
        truth["candidate_a"]["clipping_or_overlap"] = True

        scorecard = self.auditor.execute_audit(self.valid_ai_output(), truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 2.0)

    def test_rejects_metadata_only_visual_overlap_claim(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["visual_overlap_absent"] = True
        truth = copy.deepcopy(self.ground_truth)
        truth["candidate_a"]["metadata_only_difference"] = True

        scorecard = self.auditor.execute_audit(ai_output, truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 1.0)
        self.assertIn("Metadata alone", scorecard["structured_written_feedback"])

    def test_approves_loser_with_defects(self) -> None:
        """Defects in the loser should NOT cause rejection."""
        truth = copy.deepcopy(self.ground_truth)
        truth["candidate_b"]["broken_formulas"] = True

        ai_output = self.valid_ai_output()
        ai_output["winner"] = "candidate_a"

        scorecard = self.auditor.execute_audit(ai_output, truth)

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)

    # ---- Boundary / Malformed Input Tests ----

    def test_rejects_invalid_winner_value(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["winner"] = "candidate_c"

        with self.assertRaises(ValueError):
            self.auditor.execute_audit(ai_output, self.ground_truth)

    def test_rejects_missing_winner_key(self) -> None:
        ai_output = self.valid_ai_output()
        del ai_output["winner"]

        with self.assertRaises(TypeError):
            self.auditor.execute_audit(ai_output, self.ground_truth)

    def test_rejects_non_boolean_broken_formulas(self) -> None:
        truth = copy.deepcopy(self.ground_truth)
        truth["candidate_a"]["broken_formulas"] = "yes"

        with self.assertRaises(TypeError):
            self.auditor.execute_audit(self.valid_ai_output(), truth)

    def test_rejects_non_numeric_score(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["candidate_a_score"] = "high"

        with self.assertRaises(TypeError):
            self.auditor.execute_audit(ai_output, self.ground_truth)

    def test_rejects_boolean_score(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["candidate_a_score"] = True

        with self.assertRaises(TypeError):
            self.auditor.execute_audit(ai_output, self.ground_truth)

    def test_rejects_missing_candidate_in_truth(self) -> None:
        truth = copy.deepcopy(self.ground_truth)
        del truth["candidate_a"]

        with self.assertRaises(TypeError):
            self.auditor.execute_audit(self.valid_ai_output(), truth)

    def test_rejects_non_mapping_ai_output(self) -> None:
        with self.assertRaises(TypeError):
            self.auditor.execute_audit("not a dict", self.ground_truth)

    def test_rejects_non_mapping_ground_truth(self) -> None:
        with self.assertRaises(TypeError):
            self.auditor.execute_audit(self.valid_ai_output(), [1, 2, 3])

    # ---- Immutability Tests ----

    def test_inputs_not_mutated(self) -> None:
        ai_output = self.valid_ai_output()
        truth = copy.deepcopy(self.ground_truth)
        ai_snapshot = copy.deepcopy(ai_output)
        truth_snapshot = copy.deepcopy(truth)

        self.auditor.execute_audit(ai_output, truth)

        self.assertEqual(ai_output, ai_snapshot)
        self.assertEqual(truth, truth_snapshot)

    # ---- CLI Test ----

    def test_cli_produces_approved_scorecard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ai_path = Path(tmp) / "ai.json"
            truth_path = Path(tmp) / "truth.json"
            ai_path.write_text(json.dumps(self.valid_ai_output()), encoding="utf-8")
            truth_path.write_text(json.dumps(self.ground_truth), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        ROOT
                        / "evaluation_kernels"
                        / "layer_1_telemetry"
                        / "Module_10_OAPE"
                        / "oape_auditor.py"
                    ),
                    "--ai-output",
                    str(ai_path),
                    "--ground-truth",
                    str(truth_path),
                ],
                cwd=ROOT.parent,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        scorecard = json.loads(result.stdout)
        self.assertEqual(scorecard["data_quality_status"], "APPROVED")


if __name__ == "__main__":
    unittest.main()
