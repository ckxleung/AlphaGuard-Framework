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


class SecFootnoteReasoningAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        from evaluation_kernels.layer_1_telemetry.Module_05_SFRA.sfra_auditor import (
            SecFootnoteReasoningAuditor,
        )

        self.auditor = SecFootnoteReasoningAuditor()
        self.ground_truth = {
            "filing_text": (
                "Note 7 Revenue Recognition says remaining performance "
                "obligations were $42.0 million. Later, Note 12 Debt says "
                "convertible debt principal was $125.5 million."
            ),
            "footnote_boundaries": [
                {
                    "footnote_id": "N7",
                    "title": "Revenue Recognition",
                    "start_char": 0,
                    "end_char": 82,
                    "position_bucket": "middle",
                },
                {
                    "footnote_id": "N12",
                    "title": "Debt",
                    "start_char": 86,
                    "end_char": 157,
                    "position_bucket": "end",
                },
            ],
            "table_cells": [
                {
                    "cell_id": "T7.RPO",
                    "footnote_id": "N7",
                    "label": "Remaining performance obligations",
                    "value": 42.0,
                    "unit": "USD_MILLIONS",
                    "source_coordinate": "p84:note7:table1:r2:c3",
                    "position_bucket": "middle",
                },
                {
                    "cell_id": "T12.DEBT",
                    "footnote_id": "N12",
                    "label": "Convertible debt principal",
                    "value": 125.5,
                    "unit": "USD_MILLIONS",
                    "source_coordinate": "p103:note12:table2:r5:c2",
                    "position_bucket": "end",
                },
            ],
            "cross_reference_graph": [
                {
                    "question_id": "Q1",
                    "required_footnote_ids": ["N7"],
                    "required_cell_ids": ["T7.RPO"],
                },
                {
                    "question_id": "Q2",
                    "required_footnote_ids": ["N12"],
                    "required_cell_ids": ["T12.DEBT"],
                },
            ],
            "benchmark_questions": [
                {
                    "question_id": "Q1",
                    "prompt": "What were remaining performance obligations?",
                    "expected_numeric_answer": 42.0,
                    "expected_unit": "USD_MILLIONS",
                    "numeric_tolerance": 0.01,
                    "position_bucket": "middle",
                },
                {
                    "question_id": "Q2",
                    "prompt": "What was convertible debt principal?",
                    "expected_numeric_answer": 125.5,
                    "expected_unit": "USD_MILLIONS",
                    "numeric_tolerance": 0.01,
                    "position_bucket": "end",
                },
            ],
            "source_id": "DOC-SYNTHETIC-ALPHAGUARD-001",
            "filing_id": "SYNTH-10K-2026",
        }

    def valid_ai_output(self) -> dict:
        return {
            "ai_answers": [
                {
                    "question_id": "Q1",
                    "answer_text": "Remaining performance obligations were $42.0 million.",
                    "numeric_answer": 42.0,
                    "unit": "USD_MILLIONS",
                    "cited_span_ids": ["S1"],
                    "cited_cell_ids": ["T7.RPO"],
                },
                {
                    "question_id": "Q2",
                    "answer_text": "Convertible debt principal was $125.5 million.",
                    "numeric_answer": 125.5,
                    "unit": "USD_MILLIONS",
                    "cited_span_ids": ["S2"],
                    "cited_cell_ids": ["T12.DEBT"],
                },
            ],
            "cited_evidence_spans": [
                {
                    "span_id": "S1",
                    "footnote_id": "N7",
                    "source_coordinate": "p84:note7:table1:r2:c3",
                    "start_char": 0,
                    "end_char": 82,
                    "text": "Note 7 Revenue Recognition says remaining performance obligations were $42.0 million.",
                },
                {
                    "span_id": "S2",
                    "footnote_id": "N12",
                    "source_coordinate": "p103:note12:table2:r5:c2",
                    "start_char": 86,
                    "end_char": 157,
                    "text": "Note 12 Debt says convertible debt principal was $125.5 million.",
                },
            ],
        }

    def test_approves_exact_footnote_table_and_coordinate_evidence(self) -> None:
        scorecard = self.auditor.execute_audit(
            self.valid_ai_output(),
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)
        self.assertEqual(scorecard["unresolved_references"], [])
        self.assertEqual(scorecard["citation_precision"], 1.0)
        self.assertEqual(
            scorecard["position_bucket_accuracy"],
            {"middle": 1.0, "end": 1.0},
        )

    def test_rejects_missing_middle_footnote_answer(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["ai_answers"] = [ai_output["ai_answers"][1]]

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("Q1", scorecard["unresolved_references"])
        self.assertEqual(scorecard["position_bucket_accuracy"]["middle"], 0.0)

    def test_rejects_wrong_numeric_answer_and_unit(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["ai_answers"][0]["numeric_answer"] = 40.0
        ai_output["ai_answers"][0]["unit"] = "USD"

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("Q1.numeric_answer", scorecard["contradicted_values"])
        self.assertIn("Q1.unit", scorecard["contradicted_values"])

    def test_rejects_unrelated_or_missing_source_coordinates(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["cited_evidence_spans"][0]["source_coordinate"] = "p1:wrong"

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("S1.source_coordinate", scorecard["citation_defects"])

        missing_coordinate = self.valid_ai_output()
        missing_coordinate["cited_evidence_spans"][0].pop("source_coordinate")
        with self.assertRaisesRegex(ValueError, "source_coordinate"):
            self.auditor.execute_audit(missing_coordinate, self.ground_truth)

    def test_rejects_unresolved_cross_reference_graph(self) -> None:
        truth = copy.deepcopy(self.ground_truth)
        truth["cross_reference_graph"][0]["required_cell_ids"] = ["MISSING"]

        with self.assertRaisesRegex(ValueError, "cross_reference_graph"):
            self.auditor.execute_audit(self.valid_ai_output(), truth)

    def test_requires_source_and_filing_identity(self) -> None:
        missing_source = dict(self.ground_truth)
        missing_source.pop("source_id")
        with self.assertRaisesRegex(ValueError, "source_id"):
            self.auditor.execute_audit(self.valid_ai_output(), missing_source)

        missing_filing = dict(self.ground_truth)
        missing_filing.pop("filing_id")
        with self.assertRaisesRegex(ValueError, "filing_id"):
            self.auditor.execute_audit(self.valid_ai_output(), missing_filing)

    def test_inputs_are_not_mutated(self) -> None:
        ai_output = self.valid_ai_output()
        ground_truth = copy.deepcopy(self.ground_truth)
        original_ai = copy.deepcopy(ai_output)
        original_truth = copy.deepcopy(ground_truth)

        self.auditor.execute_audit(ai_output, ground_truth)

        self.assertEqual(ai_output, original_ai)
        self.assertEqual(ground_truth, original_truth)


class SecFootnoteReasoningAuditorIntegrationTests(unittest.TestCase):
    def test_manifest_registers_sfra_as_implemented(self) -> None:
        from src.module_manifest import get_module_spec

        specification = get_module_spec(5)
        self.assertEqual(specification.status, "IMPLEMENTED")
        self.assertEqual(specification.class_name, "SecFootnoteReasoningAuditor")
        self.assertTrue(specification.implementation_path.endswith("sfra_auditor.py"))

    def test_sfra_runs_as_standalone_json_cli(self) -> None:
        auditor_tests = SecFootnoteReasoningAuditorTests()
        auditor_tests.setUp()
        ai_output = auditor_tests.valid_ai_output()
        ground_truth = auditor_tests.ground_truth

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            ai_path = temporary / "ai_output.json"
            truth_path = temporary / "ground_truth.json"
            ai_path.write_text(json.dumps(ai_output), encoding="utf-8")
            truth_path.write_text(json.dumps(ground_truth), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        ROOT
                        / "evaluation_kernels"
                        / "layer_1_telemetry"
                        / "Module_05_SFRA"
                        / "sfra_auditor.py"
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
