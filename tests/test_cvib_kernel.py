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


def reference_dcf(ground_truth: dict) -> tuple[float, float, float]:
    wacc = ground_truth["wacc"]
    terminal_growth = ground_truth["terminal_growth_rate"]
    cash_flows = ground_truth["forecast_free_cash_flows"]
    present_value = sum(
        cash_flow / ((1.0 + wacc) ** year)
        for year, cash_flow in enumerate(cash_flows, start=1)
    )
    terminal_value = cash_flows[-1] * (1.0 + terminal_growth) / (
        wacc - terminal_growth
    )
    discounted_terminal_value = terminal_value / (
        (1.0 + wacc) ** len(cash_flows)
    )
    enterprise_value = present_value + discounted_terminal_value
    equity_value = enterprise_value - ground_truth["net_debt"]
    price_per_share = equity_value / ground_truth["diluted_shares"]
    return enterprise_value, equity_value, price_per_share


class CoreValuationAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        from evaluation_kernels.layer_2_valuation.Module_11_CVIB.cvib_auditor import (
            CoreValuationAuditor,
        )

        self.auditor = CoreValuationAuditor()
        self.ground_truth = {
            "forecast_free_cash_flows": [100.0, 110.0, 121.0],
            "wacc": 0.10,
            "terminal_growth_rate": 0.03,
            "net_debt": 50.0,
            "diluted_shares": 10.0,
            "currency": "USD",
            "valuation_date": "2026-06-14",
            "share_count_basis": "DILUTED_WEIGHTED_AVERAGE",
            "source_id": "DOC-SYNTHETIC-ALPHAGUARD-001",
            "valuation_relative_tolerance": 0.02,
            "multiple_relative_tolerance": 0.02,
            "comparable_company_metrics": [
                {
                    "metric_name": "EV_REVENUE_FY1",
                    "numerator_basis": "ENTERPRISE_VALUE",
                    "numerator": 1000.0,
                    "denominator": 250.0,
                    "denominator_period": "FY1_FORWARD",
                },
                {
                    "metric_name": "P_E_FY1",
                    "numerator_basis": "EQUITY_VALUE",
                    "numerator": 800.0,
                    "denominator": 100.0,
                    "denominator_period": "FY1_FORWARD",
                },
            ],
        }

    def valid_ai_output(self) -> dict:
        enterprise_value, equity_value, price_per_share = reference_dcf(
            self.ground_truth
        )
        return {
            "ai_enterprise_value": enterprise_value,
            "ai_equity_value": equity_value,
            "ai_price_per_share": price_per_share,
            "currency": "USD",
            "valuation_date": "2026-06-14",
            "share_count_basis": "DILUTED_WEIGHTED_AVERAGE",
            "terminal_value_method": "GORDON_GROWTH",
            "ai_multiples": {
                "EV_REVENUE_FY1": 4.0,
                "P_E_FY1": 8.0,
            },
        }

    def test_approves_reconciled_dcf_bridge_and_multiples(self) -> None:
        scorecard = self.auditor.execute_audit(
            self.valid_ai_output(),
            self.ground_truth,
        )

        enterprise_value, equity_value, price_per_share = reference_dcf(
            self.ground_truth
        )
        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)
        self.assertAlmostEqual(
            scorecard["ground_truth_enterprise_value"],
            enterprise_value,
        )
        self.assertAlmostEqual(scorecard["ground_truth_equity_value"], equity_value)
        self.assertAlmostEqual(
            scorecard["ground_truth_price_per_share"],
            price_per_share,
        )
        self.assertEqual(scorecard["failed_metrics"], [])
        self.assertEqual(scorecard["failed_multiples"], [])

    def test_rejects_dcf_output_beyond_tolerance(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["ai_price_per_share"] *= 1.10

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("price_per_share", scorecard["failed_metrics"])
        self.assertLess(scorecard["rigor_score"], 5.0)

    def test_rejects_inconsistent_valuation_conventions(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["currency"] = "HKD"

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["rigor_score"], 1.0)
        self.assertEqual(scorecard["convention_mismatches"], ["currency"])

    def test_rejects_multiple_deviation_and_missing_metric(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["ai_enterprise_value"] *= 1.08
        ai_output["ai_multiples"].pop("P_E_FY1")

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("enterprise_value", scorecard["failed_metrics"])
        self.assertIn("P_E_FY1", scorecard["missing_multiples"])

    def test_rejects_invalid_market_inputs(self) -> None:
        invalid_growth = {**self.ground_truth, "terminal_growth_rate": 0.11}
        with self.assertRaisesRegex(ValueError, "WACC must exceed"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_growth)

        invalid_shares = {**self.ground_truth, "diluted_shares": 0.0}
        with self.assertRaisesRegex(ValueError, "diluted_shares"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_shares)

        invalid_multiple = copy.deepcopy(self.ground_truth)
        invalid_multiple["comparable_company_metrics"][0]["denominator"] = 0.0
        with self.assertRaisesRegex(ValueError, "denominator"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_multiple)

    def test_requires_source_date_currency_and_share_basis(self) -> None:
        missing_source = dict(self.ground_truth)
        missing_source.pop("source_id")
        with self.assertRaisesRegex(ValueError, "source_id"):
            self.auditor.execute_audit(self.valid_ai_output(), missing_source)

        invalid_currency = {**self.ground_truth, "currency": "USDOLLAR"}
        with self.assertRaisesRegex(ValueError, "three-letter"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_currency)

        invalid_date = {**self.ground_truth, "valuation_date": "2026/06/14"}
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_date)

    def test_inputs_are_not_mutated(self) -> None:
        ai_output = self.valid_ai_output()
        ground_truth = copy.deepcopy(self.ground_truth)
        original_ai = copy.deepcopy(ai_output)
        original_truth = copy.deepcopy(ground_truth)

        self.auditor.execute_audit(ai_output, ground_truth)

        self.assertEqual(ai_output, original_ai)
        self.assertEqual(ground_truth, original_truth)


class CoreValuationAuditorIntegrationTests(unittest.TestCase):
    def test_manifest_registers_cvib_as_implemented(self) -> None:
        from src.module_manifest import get_module_spec

        specification = get_module_spec(11)
        self.assertEqual(specification.status, "IMPLEMENTED")
        self.assertEqual(specification.class_name, "CoreValuationAuditor")
        self.assertTrue(specification.implementation_path.endswith("cvib_auditor.py"))

    def test_cvib_runs_as_standalone_json_cli(self) -> None:
        ground_truth = {
            "forecast_free_cash_flows": [100.0, 110.0, 121.0],
            "wacc": 0.10,
            "terminal_growth_rate": 0.03,
            "net_debt": 50.0,
            "diluted_shares": 10.0,
            "currency": "USD",
            "valuation_date": "2026-06-14",
            "share_count_basis": "DILUTED_WEIGHTED_AVERAGE",
            "source_id": "DOC-SYNTHETIC-ALPHAGUARD-001",
            "comparable_company_metrics": [
                {
                    "metric_name": "EV_REVENUE_FY1",
                    "numerator_basis": "ENTERPRISE_VALUE",
                    "numerator": 1000.0,
                    "denominator": 250.0,
                    "denominator_period": "FY1_FORWARD",
                }
            ],
        }
        enterprise_value, equity_value, price_per_share = reference_dcf(
            ground_truth
        )
        ai_output = {
            "ai_enterprise_value": enterprise_value,
            "ai_equity_value": equity_value,
            "ai_price_per_share": price_per_share,
            "currency": "USD",
            "valuation_date": "2026-06-14",
            "share_count_basis": "DILUTED_WEIGHTED_AVERAGE",
            "terminal_value_method": "GORDON_GROWTH",
            "ai_multiples": {"EV_REVENUE_FY1": 4.0},
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
                        / "Module_11_CVIB"
                        / "cvib_auditor.py"
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

    def test_layer_two_smoke_executes_cvib_after_implementation(self) -> None:
        from datetime import datetime, timezone

        from src.main_pipeline import run_daily_smoke

        report = run_daily_smoke(
            "AAPL",
            observed_at=datetime(2026, 6, 14, 15, 0, tzinfo=timezone.utc),
        )

        scorecards = report["forensic_audit_scorecard"]
        self.assertIn(
            "Module_11_CVIB",
            [scorecard["kernel_id"] for scorecard in scorecards],
        )
        self.assertNotIn("Module_11_CVIB", report["unavailable_kernels"])


if __name__ == "__main__":
    unittest.main()
