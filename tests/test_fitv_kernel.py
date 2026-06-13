from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def reference_metrics(ground_truth: dict) -> tuple[float, float, float]:
    settlement = date.fromisoformat(ground_truth["settlement_date"])
    yield_rate = ground_truth["yield_to_maturity"]
    frequency = ground_truth["coupon_frequency"]
    present_values: list[tuple[float, float]] = []
    for cash_flow in ground_truth["cash_flow_schedule"]:
        payment_date = date.fromisoformat(cash_flow["payment_date"])
        years = (payment_date - settlement).days / 365.0
        discount_factor = (1.0 + yield_rate / frequency) ** (frequency * years)
        present_values.append((years, cash_flow["amount"] / discount_factor))

    dirty_price = sum(value for _, value in present_values)
    clean_price = dirty_price - ground_truth.get("accrued_interest", 0.0)
    analytical_price = (
        clean_price
        if ground_truth["price_basis"] == "CLEAN"
        else dirty_price
    )
    macaulay_duration = (
        sum(years * value for years, value in present_values) / dirty_price
    )
    modified_duration = macaulay_duration / (
        1.0 + yield_rate / frequency
    )
    dv01 = modified_duration * dirty_price * 0.0001
    return analytical_price, modified_duration, dv01


class FixedIncomeAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        from evaluation_kernels.layer_2_valuation.Module_09_FITV.fitv_auditor import (
            FixedIncomeAuditor,
        )

        self.auditor = FixedIncomeAuditor()
        self.ground_truth = {
            "cash_flow_schedule": [
                {"payment_date": "2026-07-02", "amount": 3.0},
                {"payment_date": "2027-01-01", "amount": 103.0},
            ],
            "yield_to_maturity": 0.05,
            "settlement_date": "2026-01-01",
            "day_count_convention": "ACT/365F",
            "coupon_frequency": 2,
            "face_value": 100.0,
            "currency": "USD",
            "price_basis": "DIRTY",
            "accrued_interest": 0.0,
            "source_id": "DOC-SYNTHETIC-ALPHAGUARD-001",
            "price_relative_tolerance": 0.005,
            "duration_relative_tolerance": 0.005,
            "dv01_relative_tolerance": 0.005,
        }

    def valid_ai_output(self) -> dict:
        price, duration, dv01 = reference_metrics(self.ground_truth)
        return {
            "ai_price": price,
            "ai_modified_duration": duration,
            "ai_dv01": dv01,
            "trade_thesis": "RATES_UP_PRICE_DOWN",
            "price_basis": "DIRTY",
            "day_count_convention": "ACT/365F",
            "coupon_frequency": 2,
        }

    def test_approves_reconciled_price_duration_and_dv01(self) -> None:
        scorecard = self.auditor.execute_audit(
            self.valid_ai_output(),
            self.ground_truth,
        )

        price, duration, dv01 = reference_metrics(self.ground_truth)
        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)
        self.assertAlmostEqual(scorecard["analytical_price"], price)
        self.assertAlmostEqual(scorecard["analytical_modified_duration"], duration)
        self.assertAlmostEqual(scorecard["analytical_dv01"], dv01)
        self.assertEqual(scorecard["metric_deltas"]["price"], 0.0)

    def test_supports_clean_price_with_declared_accrued_interest(self) -> None:
        truth = {**self.ground_truth, "price_basis": "CLEAN", "accrued_interest": 1.2}
        price, duration, dv01 = reference_metrics(truth)
        ai_output = {
            **self.valid_ai_output(),
            "ai_price": price,
            "ai_modified_duration": duration,
            "ai_dv01": dv01,
            "price_basis": "CLEAN",
        }

        scorecard = self.auditor.execute_audit(ai_output, truth)

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertAlmostEqual(scorecard["analytical_price"], price)

    def test_rejects_metric_deviation(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["ai_dv01"] *= 1.2

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("dv01", scorecard["failed_metrics"])

    def test_rejects_mixed_market_conventions(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["day_count_convention"] = "30/360"

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["rigor_score"], 1.0)
        self.assertEqual(
            scorecard["convention_mismatches"],
            ["day_count_convention"],
        )

    def test_rejects_rate_thesis_with_wrong_direction(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["trade_thesis"] = "RATES_UP_PRICE_UP"

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertFalse(scorecard["trade_thesis_consistent"])
        self.assertEqual(scorecard["data_quality_status"], "REJECTED")

    def test_rejects_invalid_schedule_and_market_inputs(self) -> None:
        invalid_date = copy.deepcopy(self.ground_truth)
        invalid_date["cash_flow_schedule"][0]["payment_date"] = "2025-12-31"
        with self.assertRaisesRegex(ValueError, "after settlement"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_date)

        invalid_yield = {**self.ground_truth, "yield_to_maturity": -2.0}
        with self.assertRaisesRegex(ValueError, "discount base"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_yield)

        invalid_frequency = {**self.ground_truth, "coupon_frequency": 3}
        with self.assertRaisesRegex(ValueError, "coupon_frequency"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_frequency)

        unpriceable_yield = {
            **self.ground_truth,
            "yield_to_maturity": 1e308,
        }
        with self.assertRaisesRegex(ValueError, "discount calculation"):
            self.auditor.execute_audit(
                self.valid_ai_output(),
                unpriceable_yield,
            )

    def test_requires_source_currency_and_supported_price_basis(self) -> None:
        missing_source = dict(self.ground_truth)
        missing_source.pop("source_id")
        with self.assertRaisesRegex(ValueError, "source_id"):
            self.auditor.execute_audit(self.valid_ai_output(), missing_source)

        invalid_currency = {**self.ground_truth, "currency": "$"}
        with self.assertRaisesRegex(ValueError, "three-letter"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_currency)

        invalid_basis = {**self.ground_truth, "price_basis": "MID"}
        with self.assertRaisesRegex(ValueError, "price_basis"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_basis)

    def test_inputs_are_not_mutated(self) -> None:
        ai_output = self.valid_ai_output()
        ground_truth = copy.deepcopy(self.ground_truth)
        original_ai = copy.deepcopy(ai_output)
        original_truth = copy.deepcopy(ground_truth)

        self.auditor.execute_audit(ai_output, ground_truth)

        self.assertEqual(ai_output, original_ai)
        self.assertEqual(ground_truth, original_truth)


class FixedIncomeAuditorIntegrationTests(unittest.TestCase):
    def test_manifest_registers_fitv_as_implemented(self) -> None:
        from src.module_manifest import get_module_spec

        specification = get_module_spec(9)
        self.assertEqual(specification.status, "IMPLEMENTED")
        self.assertEqual(specification.class_name, "FixedIncomeAuditor")
        self.assertTrue(specification.implementation_path.endswith("fitv_auditor.py"))

    def test_fitv_runs_as_standalone_json_cli(self) -> None:
        ground_truth = {
            "cash_flow_schedule": [
                {"payment_date": "2026-07-02", "amount": 3.0},
                {"payment_date": "2027-01-01", "amount": 103.0},
            ],
            "yield_to_maturity": 0.05,
            "settlement_date": "2026-01-01",
            "day_count_convention": "ACT/365F",
            "coupon_frequency": 2,
            "face_value": 100.0,
            "currency": "USD",
            "price_basis": "DIRTY",
            "accrued_interest": 0.0,
            "source_id": "DOC-SYNTHETIC-ALPHAGUARD-001",
        }
        price, duration, dv01 = reference_metrics(ground_truth)
        ai_output = {
            "ai_price": price,
            "ai_modified_duration": duration,
            "ai_dv01": dv01,
            "trade_thesis": "RATES_UP_PRICE_DOWN",
            "price_basis": "DIRTY",
            "day_count_convention": "ACT/365F",
            "coupon_frequency": 2,
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
                        / "Module_09_FITV"
                        / "fitv_auditor.py"
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
