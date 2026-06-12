# -*- coding: utf-8 -*-
"""Deterministic ticker-to-kernel routing for AlphaGuard smoke runs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class RoutingSpec:
    ticker: str
    target_infrastructure_layer: str
    triggered_kernels: tuple[str, ...]
    priority_level: str
    telemetry_hook: str


class TelemetryRouter:
    """Route tickers into the institutional audit layer matrix."""

    _ROUTES = {
        "NVDA": RoutingSpec(
            ticker="NVDA",
            target_infrastructure_layer="Layer_4_Institutional_Strategy",
            triggered_kernels=(
                "Module_12_IRTA",
                "Module_13_BMAE",
                "Module_15_SCGV",
            ),
            priority_level="CRITICAL_ALPHA_CAPTURE",
            telemetry_hook="EXEC_NVDA_EARNINGS_RELEASE",
        ),
        "AVGO": RoutingSpec(
            ticker="AVGO",
            target_infrastructure_layer="Layer_4_Institutional_Strategy",
            triggered_kernels=("Module_12_IRTA", "Module_15_SCGV"),
            priority_level="SUPPLY_CHAIN_ALPHA_CAPTURE",
            telemetry_hook="EXEC_AVGO_SUPPLY_CHAIN_CAPEX_UPDATE",
        ),
    }

    _DEFAULT_ROUTE = RoutingSpec(
        ticker="",
        target_infrastructure_layer="Layer_4_Institutional_Strategy",
        triggered_kernels=("Module_12_IRTA",),
        priority_level="STANDARD_RESEARCH_SURVEILLANCE",
        telemetry_hook="GENERIC_RESEARCH_THESIS_REVIEW",
    )

    def route(self, ticker: str) -> dict:
        normalized = str(ticker).strip().upper()
        if not normalized:
            raise ValueError("ticker must be a non-empty string.")

        spec = self._ROUTES.get(normalized)
        if spec is None:
            spec = RoutingSpec(
                ticker=normalized,
                target_infrastructure_layer=self._DEFAULT_ROUTE.target_infrastructure_layer,
                triggered_kernels=self._DEFAULT_ROUTE.triggered_kernels,
                priority_level=self._DEFAULT_ROUTE.priority_level,
                telemetry_hook=self._DEFAULT_ROUTE.telemetry_hook,
            )
        payload = asdict(spec)
        payload["triggered_kernels"] = list(spec.triggered_kernels)
        return payload


def route_ticker(ticker: str) -> dict:
    return TelemetryRouter().route(ticker)


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", nargs="?", default="NVDA")
    arguments = parser.parse_args()
    print(json.dumps(route_ticker(arguments.ticker), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
