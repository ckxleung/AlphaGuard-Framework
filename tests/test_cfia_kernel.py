from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class CorporateFinancialAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        from evaluation_kernels.layer_2_valuation.Module_14_CFIA.cfia_auditor import (
            CorporateFinancialAuditor,
        )

        self.auditor = CorporateFinancialAuditor()
        self.ground_truth = {
            "net_income": 5_000_000_000,
            "non_cash_adjustments": 600_000_000,
            "increase_in_net_working_capital": 520_000_000,
            "reported_operating_cash_flow": 5_080_000_000,
            "currency": "USD",
            "source_id": "SYNTHETIC-CFIA-FIXTURE",
            "fiscal_period_end": "2026-03-31",
            "absolute_tolerance": 1.0,
            "relative_tolerance": 0.000001,
        }

    def test_approves_indirect_method_ocf_within_tolerance(self) -> None:
        scorecard = self.auditor.execute_audit(
            {
                "reported_operating_cash_flow": 5_080_000_000.50,
                "methodology": (
                    "Net income plus non-cash adjustments less the increase "
                    "in net working capital."
                ),
            },
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)
        self.assertFalse(scorecard["working_capital_sign_inversion_detected"])
        self.assertEqual(scorecard["equation_deviation_delta"], 0.5)

    def test_rejects_exact_working_capital_sign_inversion(self) -> None:
        scorecard = self.auditor.execute_audit(
            {
                "reported_operating_cash_flow": 6_120_000_000,
                "methodology": (
                    "Net income plus non-cash adjustments plus the increase "
                    "in net working capital."
                ),
            },
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 1.0)
        self.assertTrue(scorecard["working_capital_sign_inversion_detected"])
        self.assertIn("sign inversion", scorecard["structured_written_feedback"])

    def test_rejects_non_inversion_ocf_variance(self) -> None:
        scorecard = self.auditor.execute_audit(
            {"reported_operating_cash_flow": 4_900_000_000},
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 3.0)
        self.assertFalse(scorecard["working_capital_sign_inversion_detected"])
        self.assertEqual(scorecard["equation_deviation_delta"], 180_000_000.0)

    def test_rejects_internally_inconsistent_ground_truth(self) -> None:
        corrupted_truth = dict(self.ground_truth)
        corrupted_truth["reported_operating_cash_flow"] = 6_000_000_000

        with self.assertRaisesRegex(ValueError, "ground truth"):
            self.auditor.execute_audit(
                {"reported_operating_cash_flow": 5_080_000_000},
                corrupted_truth,
            )

    def test_requires_explicit_working_capital_sign_convention(self) -> None:
        invalid_truth = dict(self.ground_truth)
        invalid_truth.pop("increase_in_net_working_capital")
        invalid_truth["change_in_working_capital"] = -520_000_000

        with self.assertRaisesRegex(ValueError, "increase_in_net_working_capital"):
            self.auditor.execute_audit(
                {"reported_operating_cash_flow": 5_080_000_000},
                invalid_truth,
            )

    def test_rejects_missing_and_non_finite_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "reported_operating_cash_flow"):
            self.auditor.execute_audit({}, self.ground_truth)

        invalid_truth = dict(self.ground_truth)
        invalid_truth["net_income"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            self.auditor.execute_audit(
                {"reported_operating_cash_flow": 5_080_000_000},
                invalid_truth,
            )

    def test_requires_source_and_valid_fiscal_period(self) -> None:
        missing_source = dict(self.ground_truth)
        missing_source.pop("source_id")
        with self.assertRaisesRegex(ValueError, "source_id"):
            self.auditor.execute_audit(
                {"reported_operating_cash_flow": 5_080_000_000},
                missing_source,
            )

        invalid_period = dict(self.ground_truth)
        invalid_period["fiscal_period_end"] = "2026-Q1"
        with self.assertRaisesRegex(ValueError, "fiscal_period_end"):
            self.auditor.execute_audit(
                {"reported_operating_cash_flow": 5_080_000_000},
                invalid_period,
            )

    def test_requires_three_letter_currency_code(self) -> None:
        invalid_truth = dict(self.ground_truth)
        invalid_truth["currency"] = "$"

        with self.assertRaisesRegex(ValueError, "three-letter"):
            self.auditor.execute_audit(
                {"reported_operating_cash_flow": 5_080_000_000},
                invalid_truth,
            )

    def test_input_mappings_are_not_mutated(self) -> None:
        ai_output = {"reported_operating_cash_flow": 5_080_000_000}
        ground_truth = dict(self.ground_truth)

        self.auditor.execute_audit(ai_output, ground_truth)

        self.assertEqual(ai_output, {"reported_operating_cash_flow": 5_080_000_000})
        self.assertEqual(ground_truth, self.ground_truth)


class CorporateFinancialAuditorIntegrationTests(unittest.TestCase):
    def test_manifest_registers_cfia_as_implemented(self) -> None:
        from src.module_manifest import get_module_spec

        specification = get_module_spec(14)
        self.assertEqual(specification.status, "IMPLEMENTED")
        self.assertEqual(specification.class_name, "CorporateFinancialAuditor")
        self.assertTrue(specification.implementation_path.endswith("cfia_auditor.py"))

    def test_cfia_runs_as_standalone_json_cli(self) -> None:
        ai_output = {"reported_operating_cash_flow": 5_080_000_000}
        ground_truth = {
            "net_income": 5_000_000_000,
            "non_cash_adjustments": 600_000_000,
            "increase_in_net_working_capital": 520_000_000,
            "reported_operating_cash_flow": 5_080_000_000,
            "currency": "USD",
            "source_id": "SYNTHETIC-CFIA-FIXTURE",
            "fiscal_period_end": "2026-03-31",
        }

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
                        / "layer_2_valuation"
                        / "Module_14_CFIA"
                        / "cfia_auditor.py"
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

    def test_layer_two_smoke_executes_cfia_without_fake_scorecards(self) -> None:
        from datetime import datetime, timezone

        from src.main_pipeline import run_daily_smoke

        report = run_daily_smoke(
            "AAPL",
            observed_at=datetime(2026, 6, 12, 15, 0, tzinfo=timezone.utc),
        )

        scorecards = report["forensic_audit_scorecard"]
        self.assertEqual(
            [scorecard["kernel_id"] for scorecard in scorecards],
            ["Module_14_CFIA"],
        )
        self.assertEqual(
            report["unavailable_kernels"],
            ["Module_11_CVIB", "Module_18_IBDV"],
        )


if __name__ == "__main__":
    unittest.main()
