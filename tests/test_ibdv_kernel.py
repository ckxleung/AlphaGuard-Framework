from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class InvestmentBankingDealAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        from evaluation_kernels.layer_2_valuation.Module_18_IBDV.ibdv_auditor import (
            InvestmentBankingDealAuditor,
        )

        self.auditor = InvestmentBankingDealAuditor()
        self.ground_truth = {
            "equity_value": 150_000_000_000,
            "total_debt": 25_000_000_000,
            "cash_and_equivalents": 12_000_000_000,
            "preferred_stock": 500_000_000,
            "non_controlling_interests": 4_500_000_000,
            "reported_enterprise_value": 168_000_000_000,
            "currency": "USD",
            "equity_value_basis": "TRANSACTION_EQUITY_VALUE",
            "source_id": "SYNTHETIC-IBDV-FIXTURE",
            "valuation_date": "2026-06-12",
            "absolute_tolerance": 1.0,
            "relative_tolerance": 0.000001,
        }

    def test_approves_complete_enterprise_value_bridge(self) -> None:
        scorecard = self.auditor.execute_audit(
            {"calculated_enterprise_value": 168_000_000_000.50},
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)
        self.assertEqual(scorecard["omitted_bridge_components"], [])
        self.assertEqual(scorecard["equation_deviation_delta"], 0.5)

    def test_rejects_omission_of_preferred_stock_and_nci(self) -> None:
        scorecard = self.auditor.execute_audit(
            {"calculated_enterprise_value": 163_000_000_000},
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 1.0)
        self.assertEqual(
            scorecard["omitted_bridge_components"],
            ["preferred_stock", "non_controlling_interests"],
        )
        self.assertTrue(scorecard["capital_bridge_omission_detected"])

    def test_rejects_only_non_controlling_interests_omission(self) -> None:
        scorecard = self.auditor.execute_audit(
            {"calculated_enterprise_value": 163_500_000_000},
            self.ground_truth,
        )

        self.assertEqual(scorecard["rigor_score"], 1.5)
        self.assertEqual(
            scorecard["omitted_bridge_components"],
            ["non_controlling_interests"],
        )

    def test_rejects_only_preferred_stock_omission(self) -> None:
        scorecard = self.auditor.execute_audit(
            {"calculated_enterprise_value": 167_500_000_000},
            self.ground_truth,
        )

        self.assertEqual(scorecard["rigor_score"], 1.5)
        self.assertEqual(
            scorecard["omitted_bridge_components"],
            ["preferred_stock"],
        )

    def test_rejects_generic_enterprise_value_variance(self) -> None:
        scorecard = self.auditor.execute_audit(
            {"calculated_enterprise_value": 160_000_000_000},
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 3.0)
        self.assertFalse(scorecard["capital_bridge_omission_detected"])
        self.assertEqual(scorecard["equation_deviation_delta"], 8_000_000_000.0)

    def test_rejects_internally_inconsistent_ground_truth_ev(self) -> None:
        corrupted_truth = dict(self.ground_truth)
        corrupted_truth["reported_enterprise_value"] = 170_000_000_000

        with self.assertRaisesRegex(ValueError, "ground truth"):
            self.auditor.execute_audit(
                {"calculated_enterprise_value": 168_000_000_000},
                corrupted_truth,
            )

    def test_rejects_negative_bridge_components(self) -> None:
        invalid_truth = dict(self.ground_truth)
        invalid_truth["cash_and_equivalents"] = -1

        with self.assertRaisesRegex(ValueError, "non-negative"):
            self.auditor.execute_audit(
                {"calculated_enterprise_value": 168_000_000_000},
                invalid_truth,
            )

    def test_requires_provenance_currency_and_valuation_date(self) -> None:
        missing_source = dict(self.ground_truth)
        missing_source.pop("source_id")
        with self.assertRaisesRegex(ValueError, "source_id"):
            self.auditor.execute_audit(
                {"calculated_enterprise_value": 168_000_000_000},
                missing_source,
            )

        invalid_currency = dict(self.ground_truth)
        invalid_currency["currency"] = "$"
        with self.assertRaisesRegex(ValueError, "three-letter"):
            self.auditor.execute_audit(
                {"calculated_enterprise_value": 168_000_000_000},
                invalid_currency,
            )

        invalid_date = dict(self.ground_truth)
        invalid_date["valuation_date"] = "FY2026"
        with self.assertRaisesRegex(ValueError, "valuation_date"):
            self.auditor.execute_audit(
                {"calculated_enterprise_value": 168_000_000_000},
                invalid_date,
            )

        missing_basis = dict(self.ground_truth)
        missing_basis.pop("equity_value_basis")
        with self.assertRaisesRegex(ValueError, "equity_value_basis"):
            self.auditor.execute_audit(
                {"calculated_enterprise_value": 168_000_000_000},
                missing_basis,
            )

    def test_inputs_are_not_mutated(self) -> None:
        ai_output = {"calculated_enterprise_value": 168_000_000_000}
        ground_truth = dict(self.ground_truth)

        self.auditor.execute_audit(ai_output, ground_truth)

        self.assertEqual(
            ai_output,
            {"calculated_enterprise_value": 168_000_000_000},
        )
        self.assertEqual(ground_truth, self.ground_truth)


class InvestmentBankingDealAuditorIntegrationTests(unittest.TestCase):
    def test_manifest_registers_ibdv_as_implemented(self) -> None:
        from src.module_manifest import get_module_spec

        specification = get_module_spec(18)
        self.assertEqual(specification.status, "IMPLEMENTED")
        self.assertEqual(
            specification.class_name,
            "InvestmentBankingDealAuditor",
        )
        self.assertTrue(specification.implementation_path.endswith("ibdv_auditor.py"))

    def test_ibdv_runs_as_standalone_json_cli(self) -> None:
        ai_output = {"calculated_enterprise_value": 168_000_000_000}
        ground_truth = {
            "equity_value": 150_000_000_000,
            "total_debt": 25_000_000_000,
            "cash_and_equivalents": 12_000_000_000,
            "preferred_stock": 500_000_000,
            "non_controlling_interests": 4_500_000_000,
            "reported_enterprise_value": 168_000_000_000,
            "currency": "USD",
            "equity_value_basis": "TRANSACTION_EQUITY_VALUE",
            "source_id": "SYNTHETIC-IBDV-FIXTURE",
            "valuation_date": "2026-06-12",
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
                        / "Module_18_IBDV"
                        / "ibdv_auditor.py"
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
