# -*- coding: utf-8 -*-
"""Deterministic ticker-to-kernel routing for AlphaGuard smoke runs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_CONFIG = ROOT / "config" / "target_55_enterprises.json"

LAYER_KERNELS = {
    "Layer_1_Technical_Telemetry": ("Module_05_SFRA", "Module_06_TLAB", "Module_10_OAPE"),
    "Layer_2_Quantitative_Valuation": ("Module_11_CVIB", "Module_14_CFIA", "Module_18_IBDV"),
    "Layer_3_Regulatory_Compliance": ("Module_17_ERCA", "Module_01_FRTE", "Module_08_FOAS"),
    "Layer_4_Institutional_Strategy": ("Module_12_IRTA", "Module_13_BMAE", "Module_15_SCGV"),
}

LAYER_PRIORITIES = {
    "Layer_1_Technical_Telemetry": "TECHNICAL_TELEMETRY_SURVEILLANCE",
    "Layer_2_Quantitative_Valuation": "VALUATION_INTEGRITY_SURVEILLANCE",
    "Layer_3_Regulatory_Compliance": "REGULATORY_COMPLIANCE_SURVEILLANCE",
    "Layer_4_Institutional_Strategy": "INSTITUTIONAL_STRATEGY_SURVEILLANCE",
}


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

    def __init__(self, config_path: Path | str = DEFAULT_TARGET_CONFIG) -> None:
        self._enterprise_layers = self._load_enterprise_layers(Path(config_path))

    @staticmethod
    def _load_enterprise_layers(config_path: Path) -> dict[str, str]:
        if not config_path.is_file():
            raise FileNotFoundError(f"Missing target enterprise config: {config_path}")

        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw_config, dict):
            raise ValueError("target enterprise config must be a layer-to-tickers object.")

        enterprise_layers: dict[str, str] = {}
        for layer_name, tickers in raw_config.items():
            if layer_name not in LAYER_KERNELS:
                raise ValueError(f"Unknown infrastructure layer in config: {layer_name}")
            if not isinstance(tickers, list) or not tickers:
                raise ValueError(f"Layer {layer_name} must define a non-empty ticker list.")

            for ticker in tickers:
                normalized = str(ticker).strip().upper()
                if not normalized:
                    raise ValueError(f"Layer {layer_name} contains a blank ticker.")
                previous_layer = enterprise_layers.get(normalized)
                if previous_layer and previous_layer != layer_name:
                    raise ValueError(
                        f"Ticker {normalized} is assigned to both "
                        f"{previous_layer} and {layer_name}."
                    )
                enterprise_layers[normalized] = layer_name

        if len(enterprise_layers) != 55:
            raise ValueError(
                "target enterprise config must contain exactly 55 unique tickers."
            )
        return enterprise_layers

    def route(self, ticker: str) -> dict:
        normalized = str(ticker).strip().upper()
        if not normalized:
            raise ValueError("ticker must be a non-empty string.")

        spec = self._ROUTES.get(normalized)
        if spec is None:
            layer = self._enterprise_layers.get(normalized)
            if layer:
                spec = RoutingSpec(
                    ticker=normalized,
                    target_infrastructure_layer=layer,
                    triggered_kernels=LAYER_KERNELS[layer],
                    priority_level=LAYER_PRIORITIES[layer],
                    telemetry_hook=f"TARGET_55_ENTERPRISE_{normalized}_DAILY_LOOP",
                )
            else:
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
