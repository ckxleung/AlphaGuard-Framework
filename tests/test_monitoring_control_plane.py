from __future__ import annotations

import json
import math
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PUBLIC_DOCUMENT_ID = "DOC-ALPHAGUARD-RESEARCH-20260613-001"
SYNTHETIC_DOCUMENT_ID = "DOC-SYNTHETIC-ALPHAGUARD-001"


class MonitoringPolicyTests(unittest.TestCase):
    def test_all_current_targets_have_one_valid_cohort_profile(self) -> None:
        from src.monitoring_control_plane import load_enterprise_profiles

        profiles = load_enterprise_profiles()
        self.assertEqual(len(profiles), 56)
        self.assertEqual(len(set(profiles)), 56)
        self.assertEqual(
            profiles["00100.HK"]["cohort"],
            "FOUNDATIONAL_API",
        )
        self.assertEqual(
            profiles["00100.HK"]["functional_layer"],
            "Layer_1_Technical_Telemetry",
        )
        self.assertEqual(
            {profile["cohort"] for profile in profiles.values()},
            {
                "FOUNDATIONAL_API",
                "ENTERPRISE_FINTECH_AGENT",
                "COMPUTE_INFRASTRUCTURE",
            },
        )
        self.assertEqual(
            profiles["NVDA"]["functional_layer"],
            "Layer_4_Institutional_Strategy",
        )
        self.assertEqual(
            profiles["MSFT"]["functional_layer"],
            "Layer_1_Technical_Telemetry",
        )

    def test_daily_baseline_selects_exactly_two_modules(self) -> None:
        from src.monitoring_control_plane import plan_monitoring_event

        plan = plan_monitoring_event(
            {
                "event_id": "evt-baseline-msft",
                "ticker": "MSFT",
                "event_type": "DAILY_BASELINE",
                "observed_at": "2026-06-13T00:00:00Z",
                "evidence_refs": [],
                "data_classification": "PLANNING_ONLY",
            }
        )

        self.assertEqual(plan["selected_modules"], ["TLAB", "BMAE"])
        self.assertEqual(
            plan["target_infrastructure_layer"],
            "Layer_1_Technical_Telemetry",
        )
        self.assertEqual(plan["executable_modules"], ["BMAE"])
        self.assertEqual(plan["unavailable_modules"], ["TLAB"])
        self.assertFalse(plan["publication_eligible"])

    def test_event_peak_selects_between_three_and_five_modules(self) -> None:
        from src.monitoring_control_plane import plan_monitoring_event

        plan = plan_monitoring_event(
            {
                "event_id": "evt-earnings-aapl",
                "ticker": "AAPL",
                "event_type": "EARNINGS_RELEASE",
                "observed_at": "2026-06-13T01:00:00Z",
                "evidence_refs": [PUBLIC_DOCUMENT_ID],
                "data_classification": "PUBLIC_SOURCE",
            }
        )

        self.assertGreaterEqual(len(plan["selected_modules"]), 3)
        self.assertLessEqual(len(plan["selected_modules"]), 5)
        self.assertEqual(
            plan["selected_modules"],
            ["FRTE", "CFIA", "CVIB", "IRTA", "IBDV"],
        )
        self.assertEqual(plan["cohort"], "ENTERPRISE_FINTECH_AGENT")
        self.assertEqual(plan["cohort_event_priority"], "PREFERRED")
        self.assertIn("FRTE", plan["unavailable_modules"])
        self.assertFalse(plan["publication_eligible"])

    def test_unknown_event_type_and_ticker_fail_closed(self) -> None:
        from src.monitoring_control_plane import plan_monitoring_event

        with self.assertRaisesRegex(ValueError, "event_type"):
            plan_monitoring_event(
                {
                    "event_id": "evt-invalid",
                    "ticker": "MSFT",
                    "event_type": "EVERYTHING",
                    "observed_at": "2026-06-13T00:00:00Z",
                    "evidence_refs": [],
                    "data_classification": "PLANNING_ONLY",
                }
            )

    def test_rate_shock_exposes_fitv_as_executable(self) -> None:
        from src.monitoring_control_plane import plan_monitoring_event

        plan = plan_monitoring_event(
            {
                "event_id": "evt-rate-shock-aapl",
                "ticker": "AAPL",
                "event_type": "RATE_SHOCK",
                "observed_at": "2026-06-13T03:00:00Z",
                "evidence_refs": [PUBLIC_DOCUMENT_ID],
                "data_classification": "PUBLIC_SOURCE",
            }
        )

        self.assertIn("FITV", plan["executable_modules"])
        self.assertIn("CVIB", plan["executable_modules"])
        self.assertNotIn("CVIB", plan["unavailable_modules"])
        with self.assertRaisesRegex(ValueError, "ticker"):
            plan_monitoring_event(
                {
                    "event_id": "evt-unknown",
                    "ticker": "UNKNOWN",
                    "event_type": "DAILY_BASELINE",
                    "observed_at": "2026-06-13T00:00:00Z",
                    "evidence_refs": [],
                    "data_classification": "PLANNING_ONLY",
                }
            )

    def test_portfolio_baseline_builds_current_non_publishable_plans(self) -> None:
        from src.monitoring_control_plane import plan_portfolio_baseline

        report = plan_portfolio_baseline("2026-06-13T00:00:00Z")
        self.assertEqual(report["target_count"], 56)
        self.assertEqual(len(report["plans"]), 56)
        self.assertFalse(report["publication_eligible"])
        self.assertTrue(
            all(not plan["publication_eligible"] for plan in report["plans"])
        )


class SelectiveExecutionTests(unittest.TestCase):
    @staticmethod
    def _module_payloads(
        classification: str = "PUBLIC_SOURCE",
        evidence_ref: str = PUBLIC_DOCUMENT_ID,
    ) -> dict:
        safety_stock = 1.65 * math.sqrt(10 * 20**2 + 100**2 * 2**2)
        return {
            "BMAE": {
                "data_classification": classification,
                "evidence_refs": [evidence_ref],
                "ai_output": {
                    "sentiment_changes": [0.1, 0.2, 0.3, 0.4],
                    "rating": "Buy",
                },
                "ground_truth": {
                    "block_trades_outflow": [-5.0, -8.0, -10.0, -12.0],
                    "retail_orderflow_imbalance": [2.0, 3.0, 4.0, 5.0],
                    "discussion_volume": [100.0, 110.0, 120.0, 130.0],
                    "price_changes": [0.01, 0.02, 0.02, 0.03],
                },
            },
            "SCGV": {
                "data_classification": classification,
                "evidence_refs": [evidence_ref],
                "ai_output": {
                    "reorder_point": 1000.0 + safety_stock,
                    "safety_stock": safety_stock,
                    "methodology": "Dual-variance stochastic equation.",
                },
                "ground_truth": {
                    "average_demand": 100.0,
                    "average_lead_time": 10.0,
                    "demand_std": 20.0,
                    "lead_time_std": 2.0,
                    "service_level": 0.95,
                },
            },
        }

    def test_pipeline_executes_only_supplied_selected_module_payloads(self) -> None:
        from src.main_pipeline import run_module_payloads

        report = run_module_payloads(
            self._module_payloads(),
            selected_codes=("BMAE",),
        )
        self.assertEqual(report["executed_modules"], 1)
        self.assertEqual(set(report["results"]), {"BMAE"})

    def test_control_plane_executes_available_modules_and_discloses_gaps(
        self,
    ) -> None:
        from src.monitoring_control_plane import execute_monitoring_event

        report = execute_monitoring_event(
            {
                "event_id": "evt-supply-nvda",
                "ticker": "NVDA",
                "event_type": "SUPPLY_CHAIN_DISRUPTION",
                "observed_at": "2026-06-13T02:00:00Z",
                "evidence_refs": [PUBLIC_DOCUMENT_ID],
                "data_classification": "PUBLIC_SOURCE",
            },
            self._module_payloads(),
        )

        self.assertEqual(set(report["results"]), {"BMAE", "SCGV"})
        self.assertIn("APAC", report["unavailable_modules"])
        self.assertIn("IRTA", report["skipped_executable_modules"])
        self.assertFalse(report["publication_eligible"])

    def test_synthetic_execution_is_never_publication_eligible(self) -> None:
        from src.monitoring_control_plane import execute_monitoring_event

        report = execute_monitoring_event(
            {
                "event_id": "evt-synthetic",
                "ticker": "NVDA",
                "event_type": "SUPPLY_CHAIN_DISRUPTION",
                "observed_at": "2026-06-13T02:00:00Z",
                "evidence_refs": [SYNTHETIC_DOCUMENT_ID],
                "data_classification": "SYNTHETIC",
            },
            self._module_payloads(
                classification="SYNTHETIC",
                evidence_ref=SYNTHETIC_DOCUMENT_ID,
            ),
        )
        self.assertFalse(report["publication_eligible"])

    def test_payload_provenance_must_match_event(self) -> None:
        from src.monitoring_control_plane import execute_monitoring_event

        with self.assertRaisesRegex(ValueError, "data_classification"):
            execute_monitoring_event(
                {
                    "event_id": "evt-provenance",
                    "ticker": "NVDA",
                    "event_type": "SUPPLY_CHAIN_DISRUPTION",
                    "observed_at": "2026-06-13T02:00:00Z",
                    "evidence_refs": [PUBLIC_DOCUMENT_ID],
                    "data_classification": "PUBLIC_SOURCE",
                },
                self._module_payloads(
                    classification="SYNTHETIC",
                    evidence_ref=SYNTHETIC_DOCUMENT_ID,
                ),
            )

    def test_unregistered_event_evidence_fails_closed(self) -> None:
        from src.monitoring_control_plane import plan_monitoring_event

        with self.assertRaisesRegex(ValueError, "not registered"):
            plan_monitoring_event(
                {
                    "event_id": "evt-unregistered-source",
                    "ticker": "NVDA",
                    "event_type": "SUPPLY_CHAIN_DISRUPTION",
                    "observed_at": "2026-06-13T02:00:00Z",
                    "evidence_refs": ["DOC-UNKNOWN"],
                    "data_classification": "PUBLIC_SOURCE",
                }
            )

    def test_control_plane_cli_runs_sample_event(self) -> None:
        event_path = ROOT / "examples" / "monitoring_event.example.json"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "src" / "monitoring_control_plane.py"),
                "--event",
                str(event_path),
            ],
            cwd=ROOT.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["event_type"], "FINANCING_MA")
        self.assertFalse(payload["publication_eligible"])


if __name__ == "__main__":
    unittest.main()
