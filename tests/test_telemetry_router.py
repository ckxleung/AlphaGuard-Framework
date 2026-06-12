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

    def test_unknown_ticker_uses_default_research_surveillance_route(self) -> None:
        route = TelemetryRouter().route("unknown")

        self.assertEqual(route["ticker"], "UNKNOWN")
        self.assertEqual(route["priority_level"], "STANDARD_RESEARCH_SURVEILLANCE")
        self.assertEqual(route["triggered_kernels"], ["Module_12_IRTA"])

    def test_router_rejects_blank_ticker(self) -> None:
        with self.assertRaisesRegex(ValueError, "ticker"):
            route_ticker(" ")


if __name__ == "__main__":
    unittest.main()
