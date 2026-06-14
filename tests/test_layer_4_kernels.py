from __future__ import annotations

import math
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation_kernels.layer_4_strategy.Module_12_IRTA.institutional_research_thesis_auditor import (
    InstitutionalResearchThesisAuditor,
)
from evaluation_kernels.layer_4_strategy.Module_13_BMAE.behavioral_market_auditor import (
    BehavioralMarketAuditor,
)
from evaluation_kernels.layer_4_strategy.Module_15_SCGV.supply_chain_auditor import (
    SupplyChainAuditor,
)


class InstitutionalResearchThesisAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auditor = InstitutionalResearchThesisAuditor()
        self.ground_truth = {
            "current_capacity": 100.0,
            "capex_additions": [10.0, 10.0, 10.0, 10.0, 10.0],
            "capital_efficiency": 2.0,
            "max_utilization": 0.90,
            "blended_asp": 5.0,
        }

    def test_rejects_bullish_revenue_above_physical_capacity(self) -> None:
        scorecard = self.auditor.execute_audit(
            {
                "revenue_forecast": [500.0, 600.0, 700.0, 850.0, 1100.0],
                "investment_thesis": "Capacity expands rapidly; strong buy.",
            },
            self.ground_truth,
        )

        self.assertTrue(scorecard["capacity_ceiling_breached"])
        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(scorecard["rigor_score"], 2.0)
        self.assertGreater(scorecard["implied_utilization_rate"], 1.0)

    def test_approves_forecast_within_five_year_capacity_ceiling(self) -> None:
        scorecard = self.auditor.execute_audit(
            {"revenue_forecast": [400.0, 450.0, 500.0, 550.0, 600.0]},
            self.ground_truth,
        )

        self.assertFalse(scorecard["capacity_ceiling_breached"])
        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertAlmostEqual(scorecard["forecast_cagr"], (600 / 400) ** 0.25 - 1)

    def test_rejects_invalid_utilization_and_forecast_length(self) -> None:
        invalid_truth = dict(self.ground_truth)
        invalid_truth["max_utilization"] = 1.1
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            self.auditor.execute_audit(
                {"revenue_forecast": [1, 2, 3, 4, 5]},
                invalid_truth,
            )
        with self.assertRaisesRegex(ValueError, "exactly five"):
            self.auditor.execute_audit(
                {"revenue_forecast": [1, 2]},
                self.ground_truth,
            )


class BehavioralMarketAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auditor = BehavioralMarketAuditor()

    def test_rejects_strong_buy_during_discussion_spike_and_block_outflow(self) -> None:
        scorecard = self.auditor.execute_audit(
            {
                "sentiment_changes": [0.1, 0.4, 0.8, 1.2],
                "rating": "Strong Buy",
            },
            {
                "block_trades_outflow": [10.0, 20.0, 30.0, 40.0],
                "retail_orderflow_imbalance": [2.0, 2.0, 2.0, 2.0],
                "discussion_volume": [100.0, 110.0, 120.0, 400.0],
                "price_changes": [0.01, 0.00, -0.01, -0.02],
            },
        )

        self.assertTrue(scorecard["noise_filter_failed"])
        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertGreater(scorecard["noise_inflation_ratio"], 1.0)
        self.assertTrue(math.isfinite(scorecard["signal_to_noise_db"]))

    def test_approves_supported_sentiment_signal(self) -> None:
        scorecard = self.auditor.execute_audit(
            {
                "sentiment_changes": [0.1, 0.2, 0.3, 0.4],
                "rating": "Buy",
            },
            {
                "block_trades_outflow": [-5.0, -8.0, -10.0, -12.0],
                "retail_orderflow_imbalance": [2.0, 3.0, 4.0, 5.0],
                "discussion_volume": [100.0, 110.0, 120.0, 130.0],
                "price_changes": [0.01, 0.02, 0.02, 0.03],
            },
        )

        self.assertFalse(scorecard["noise_filter_failed"])
        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertIn("signal_purity_coefficient", scorecard)

    def test_rejects_zero_retail_imbalance_and_misaligned_series(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot contain zero"):
            self.auditor.execute_audit(
                {"sentiment_changes": [0.1, 0.2, 0.3]},
                {
                    "block_trades_outflow": [1.0, 2.0, 3.0],
                    "retail_orderflow_imbalance": [1.0, 0.0, 1.0],
                    "discussion_volume": [10.0, 11.0, 12.0],
                    "price_changes": [0.01, 0.02, 0.03],
                },
            )
        with self.assertRaisesRegex(ValueError, "must align"):
            self.auditor.execute_audit(
                {"sentiment_changes": [0.1, 0.2, 0.3]},
                {
                    "block_trades_outflow": [1.0, 2.0, 3.0, 4.0],
                    "retail_orderflow_imbalance": [1.0, 1.0, 1.0, 1.0],
                    "discussion_volume": [10.0, 11.0, 12.0, 13.0],
                    "price_changes": [0.01, 0.02, 0.03, 0.04],
                },
            )


class SupplyChainAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.auditor = SupplyChainAuditor()
        self.ground_truth = {
            "average_demand": 100.0,
            "average_lead_time": 10.0,
            "demand_std": 20.0,
            "lead_time_std": 2.0,
            "service_level": 0.95,
        }

    def test_accepts_stochastic_reorder_point_equation(self) -> None:
        safety_stock = 1.65 * math.sqrt(10 * 20**2 + 100**2 * 2**2)
        expected_rop = 100 * 10 + safety_stock
        scorecard = self.auditor.execute_audit(
            {
                "reorder_point": expected_rop,
                "safety_stock": safety_stock,
                "methodology": "Dual-variance stochastic safety-stock equation.",
            },
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertAlmostEqual(scorecard["inventory_stockout_risk_pct"], 5.0)
        self.assertAlmostEqual(scorecard["equation_deviation_delta"], 0.0)

    def test_rejects_linear_variance_shortcut(self) -> None:
        linear_safety_stock = 1.65 * (20.0 + 2.0)
        scorecard = self.auditor.execute_audit(
            {
                "reorder_point": 1000.0 + linear_safety_stock,
                "safety_stock": linear_safety_stock,
                "methodology": "Linear addition of uncertainty.",
            },
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertTrue(scorecard["linear_shortcut_detected"])
        self.assertGreater(scorecard["equation_deviation_delta"], 0.0)

    def test_rejects_unknown_service_level_without_z_score(self) -> None:
        invalid_ground_truth = dict(self.ground_truth)
        invalid_ground_truth["service_level"] = 0.975

        with self.assertRaisesRegex(ValueError, "z_score"):
            self.auditor.execute_audit(
                {"reorder_point": 1000.0, "safety_stock": 0.0},
                invalid_ground_truth,
            )

    def test_accepts_explicit_z_score_for_custom_service_level(self) -> None:
        custom_truth = dict(self.ground_truth)
        custom_truth.update({"service_level": 0.975, "z_score": 1.96})
        safety_stock = 1.96 * math.sqrt(10 * 20**2 + 100**2 * 2**2)
        scorecard = self.auditor.execute_audit(
            {
                "reorder_point": 1000.0 + safety_stock,
                "safety_stock": safety_stock,
            },
            custom_truth,
        )
        self.assertEqual(scorecard["data_quality_status"], "APPROVED")


class ManifestIntegrationTests(unittest.TestCase):
    def test_three_completed_specs_are_registered_as_implemented(self) -> None:
        from src.module_manifest import get_module_spec

        expected = {
            12: ("IRTA", "InstitutionalResearchThesisAuditor"),
            13: ("BMAE", "BehavioralMarketAuditor"),
            15: ("SCGV", "SupplyChainAuditor"),
        }
        for module_id, (code, class_name) in expected.items():
            specification = get_module_spec(module_id)
            self.assertEqual(specification.code, code)
            self.assertEqual(specification.class_name, class_name)
            self.assertEqual(specification.status, "IMPLEMENTED")
            self.assertTrue(specification.implementation_path)

    def test_unknown_module_id_fails_closed(self) -> None:
        from src.module_manifest import get_module_spec

        with self.assertRaises(KeyError):
            get_module_spec(99)

    def test_main_pipeline_executes_all_eighteen_completed_kernels(self) -> None:
        from src.main_pipeline import run_pipeline, _daily_smoke_inputs
        ai_output, ground_truth = _daily_smoke_inputs()
        results = run_pipeline(ai_output, ground_truth)
        self.assertIn("results", results)
        self.assertEqual(results["executed_modules"], 18)

    def test_each_kernel_runs_as_a_standalone_json_cli(self) -> None:
        safety_stock = 1.65 * math.sqrt(10 * 20**2 + 100**2 * 2**2)
        ai_output = {
            "revenue_forecast": [400.0, 450.0, 500.0, 550.0, 600.0],
            "sentiment_changes": [0.1, 0.2, 0.3, 0.4],
            "rating": "Buy",
            "reorder_point": 1000.0 + safety_stock,
            "safety_stock": safety_stock,
            "methodology": "Dual-variance stochastic equation.",
        }
        ground_truth = {
            "current_capacity": 100.0,
            "capex_additions": [10.0, 10.0, 10.0, 10.0, 10.0],
            "capital_efficiency": 2.0,
            "max_utilization": 0.90,
            "blended_asp": 5.0,
            "block_trades_outflow": [-5.0, -8.0, -10.0, -12.0],
            "retail_orderflow_imbalance": [2.0, 3.0, 4.0, 5.0],
            "discussion_volume": [100.0, 110.0, 120.0, 130.0],
            "price_changes": [0.01, 0.02, 0.02, 0.03],
            "average_demand": 100.0,
            "average_lead_time": 10.0,
            "demand_std": 20.0,
            "lead_time_std": 2.0,
            "service_level": 0.95,
        }
        scripts = (
            ROOT
            / "evaluation_kernels/layer_4_strategy/Module_12_IRTA/"
            "institutional_research_thesis_auditor.py",
            ROOT
            / "evaluation_kernels/layer_4_strategy/Module_13_BMAE/"
            "behavioral_market_auditor.py",
            ROOT
            / "evaluation_kernels/layer_4_strategy/Module_15_SCGV/"
            "supply_chain_auditor.py",
        )

        with tempfile.TemporaryDirectory() as directory:
            temp_dir = Path(directory)
            ai_path = temp_dir / "ai_output.json"
            truth_path = temp_dir / "ground_truth.json"
            ai_path.write_text(json.dumps(ai_output), encoding="utf-8")
            truth_path.write_text(json.dumps(ground_truth), encoding="utf-8")

            for script in scripts:
                result = subprocess.run(
                    [
                        sys.executable,
                        str(script),
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
