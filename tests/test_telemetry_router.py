from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.telemetry_router import TelemetryRouter, route_ticker


class TelemetryRouterTests(unittest.TestCase):
    def test_nvda_routes_to_critical_layer_four_strategy(self) -> None:
        route = route_ticker("NVDA")

        self.assertEqual(route["ticker"], "NVDA")
        self.assertEqual(
            route["target_infrastructure_layer"],
            "Layer_4_Institutional_Strategy",
        )
        self.assertEqual(route["priority_level"], "CRITICAL_ALPHA_CAPTURE")
        self.assertIn("Module_12_IRTA", route["triggered_kernels"])
        self.assertIn("Module_13_BMAE", route["triggered_kernels"])
        self.assertIn("Module_15_SCGV", route["triggered_kernels"])

    def test_configured_layer_one_ticker_routes_from_enterprise_matrix(self) -> None:
        route = route_ticker("MSFT")

        self.assertEqual(route["ticker"], "MSFT")
        self.assertEqual(
            route["target_infrastructure_layer"],
            "Layer_1_Technical_Telemetry",
        )
        self.assertEqual(route["priority_level"], "TECHNICAL_TELEMETRY_SURVEILLANCE")
        self.assertEqual(
            route["triggered_kernels"],
            ["Module_05_SFRA", "Module_06_TLAB", "Module_10_OAPE"],
        )

    def test_minimax_routes_to_layer_one_foundational_telemetry(self) -> None:
        route = route_ticker("00100.HK")

        self.assertEqual(route["ticker"], "00100.HK")
        self.assertEqual(
            route["target_infrastructure_layer"],
            "Layer_1_Technical_Telemetry",
        )
        self.assertEqual(
            route["triggered_kernels"],
            ["Module_05_SFRA", "Module_06_TLAB", "Module_10_OAPE"],
        )

    def test_configured_layer_two_ticker_routes_from_enterprise_matrix(self) -> None:
        route = route_ticker("AAPL")

        self.assertEqual(
            route["target_infrastructure_layer"],
            "Layer_2_Quantitative_Valuation",
        )
        self.assertEqual(route["priority_level"], "VALUATION_INTEGRITY_SURVEILLANCE")

    def test_configured_layer_three_ticker_routes_from_enterprise_matrix(self) -> None:
        route = route_ticker("TSLA")

        self.assertEqual(
            route["target_infrastructure_layer"],
            "Layer_3_Regulatory_Compliance",
        )
        self.assertEqual(route["priority_level"], "REGULATORY_COMPLIANCE_SURVEILLANCE")

    def test_event_route_uses_authoritative_policy_modules(self) -> None:
        route = route_ticker("NVDA", market_event="earnings_release")

        self.assertEqual(route["ticker"], "NVDA")
        self.assertEqual(route["market_event"], "EARNINGS_RELEASE")
        self.assertEqual(route["priority_level"], "CRITICAL_ALPHA_CAPTURE")
        self.assertEqual(
            route["triggered_kernels"],
            [
                "Module_01_FRTE",
                "Module_14_CFIA",
                "Module_11_CVIB",
                "Module_12_IRTA",
                "Module_18_IBDV",
            ],
        )

    def test_supply_chain_event_routes_to_strategy_and_supply_chain_stack(self) -> None:
        route = route_ticker("300308.SZ", market_event="supply_chain_disruption")

        self.assertEqual(
            route["target_infrastructure_layer"],
            "Layer_4_Institutional_Strategy",
        )
        self.assertEqual(route["priority_level"], "SUPPLY_CHAIN_ALPHA_CAPTURE")
        self.assertEqual(
            route["triggered_kernels"],
            [
                "Module_02_APAC",
                "Module_15_SCGV",
                "Module_12_IRTA",
                "Module_13_BMAE",
            ],
        )

    def test_rate_shock_routes_to_fixed_income_valuation_stack(self) -> None:
        route = route_ticker("AAPL", market_event="rate_shock")

        self.assertEqual(route["priority_level"], "FIXED_INCOME_REPRICING_ALARM")
        self.assertEqual(
            route["triggered_kernels"],
            [
                "Module_09_FITV",
                "Module_11_CVIB",
                "Module_14_CFIA",
            ],
        )

    def test_sh_and_ss_suffixes_are_normalized_against_target_universe(self) -> None:
        route_from_sh = route_ticker("603083.SH")
        route_from_ss = route_ticker("603083.SS")

        self.assertEqual(route_from_sh["ticker"], "603083.SS")
        self.assertEqual(route_from_ss["ticker"], "603083.SS")
        self.assertEqual(
            route_from_sh["target_infrastructure_layer"],
            "Layer_4_Institutional_Strategy",
        )

    def test_unknown_ticker_uses_default_research_surveillance_route(self) -> None:
        route = TelemetryRouter().route("unknown")

        self.assertEqual(route["ticker"], "UNKNOWN")
        self.assertEqual(route["priority_level"], "STANDARD_RESEARCH_SURVEILLANCE")
        self.assertEqual(route["triggered_kernels"], ["Module_12_IRTA"])

    def test_router_rejects_blank_ticker(self) -> None:
        with self.assertRaisesRegex(ValueError, "ticker"):
            route_ticker(" ")

    def test_main_pipeline_event_smoke_executes_only_available_event_kernels(self) -> None:
        from datetime import datetime, timezone

        from src.main_pipeline import run_daily_smoke

        report = run_daily_smoke(
            "NVDA",
            market_event="earnings_release",
            observed_at=datetime(2026, 6, 13, 0, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(report["routing_specs"]["market_event"], "EARNINGS_RELEASE")
        self.assertEqual(
            [scorecard["kernel_id"] for scorecard in report["forensic_audit_scorecard"]],
            [
                "Module_14_CFIA",
                "Module_11_CVIB",
                "Module_12_IRTA",
                "Module_18_IBDV",
            ],
        )
        self.assertEqual(
            report["unavailable_kernels"],
            ["Module_01_FRTE"],
        )
        self.assertFalse(report["substack_ready_flag"])

    def test_layer_three_smoke_executes_foas_after_implementation(self) -> None:
        from datetime import datetime, timezone

        from src.main_pipeline import run_daily_smoke

        report = run_daily_smoke(
            "TSLA",
            observed_at=datetime(2026, 6, 14, 15, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(
            report["routing_specs"]["target_infrastructure_layer"],
            "Layer_3_Regulatory_Compliance",
        )
        self.assertIn(
            "Module_08_FOAS",
            [scorecard["kernel_id"] for scorecard in report["forensic_audit_scorecard"]],
        )
        self.assertEqual(
            report["unavailable_kernels"],
            ["Module_17_ERCA", "Module_01_FRTE"],
        )


if __name__ == "__main__":
    unittest.main()
