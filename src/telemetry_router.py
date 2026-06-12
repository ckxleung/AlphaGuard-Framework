# -*- coding: utf-8 -*-
"""Deterministic ticker-to-kernel routing for AlphaGuard smoke runs."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_TARGET_CONFIG = ROOT / "config" / "target_enterprises.json"
DEFAULT_EVENT_POLICY = ROOT / "config" / "event_routing_policy.json"

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
EVENT_PRIORITIES = {
    "API_CHANGE": "TECHNICAL_BREAKING_CHANGE_ALARM",
    "MODEL_RELEASE": "MODEL_RELEASE_TELEMETRY_ALARM",
    "EARNINGS_RELEASE": "CRITICAL_ALPHA_CAPTURE",
    "FINANCING_MA": "CRITICAL_DEAL_VALIDATION",
    "REGULATORY_UPDATE": "HIGH_COMPLIANCE_ALARM",
    "REGULATORY_CHANGE": "HIGH_COMPLIANCE_ALARM",
    "SUPPLY_CHAIN_DISRUPTION": "SUPPLY_CHAIN_ALPHA_CAPTURE",
    "ARTIFACT_RELEASE": "INSTITUTIONAL_ARTIFACT_REVIEW",
    "ML_MODEL_UPDATE": "MODEL_VALIDATION_ALARM",
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

    def __init__(
        self,
        config_path: Path | str = DEFAULT_TARGET_CONFIG,
        event_policy_path: Path | str = DEFAULT_EVENT_POLICY,
    ) -> None:
        target_path = Path(config_path)
        self._enterprise_layers = self._load_enterprise_layers(target_path)
        self._canonical_aliases = self._load_canonical_aliases(target_path)
        self._event_routes = self._load_event_routes(Path(event_policy_path))

    @staticmethod
    def _ticker_aliases(ticker: str) -> tuple[str, ...]:
        normalized = str(ticker).strip().upper()
        aliases = [normalized]
        if normalized.endswith(".SH"):
            aliases.append(normalized[:-3] + ".SS")
        elif normalized.endswith(".SS"):
            aliases.append(normalized[:-3] + ".SH")
        return tuple(dict.fromkeys(aliases))

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
                aliases = TelemetryRouter._ticker_aliases(str(ticker))
                normalized = aliases[0]
                if not normalized:
                    raise ValueError(f"Layer {layer_name} contains a blank ticker.")
                for alias in aliases:
                    previous_layer = enterprise_layers.get(alias)
                    if previous_layer and previous_layer != layer_name:
                        raise ValueError(
                            f"Ticker {alias} is assigned to both "
                            f"{previous_layer} and {layer_name}."
                        )
                    enterprise_layers[alias] = layer_name

        canonical_ticker_list = [
            str(ticker).strip().upper()
            for tickers in raw_config.values()
            for ticker in tickers
        ]
        if not canonical_ticker_list:
            raise ValueError(
                "target enterprise config must contain at least one ticker."
            )
        if len(canonical_ticker_list) != len(set(canonical_ticker_list)):
            raise ValueError("target enterprise config contains duplicate tickers.")
        return enterprise_layers

    @staticmethod
    def _load_event_routes(policy_path: Path) -> dict[str, tuple[str, ...]]:
        if not policy_path.is_file():
            raise FileNotFoundError(f"Missing event routing policy: {policy_path}")
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("event routing policy must be a JSON object.")
        raw_routes = payload.get("event_routes")
        if not isinstance(raw_routes, dict) or not raw_routes:
            raise ValueError("event_routes must be a non-empty object.")
        event_routes: dict[str, tuple[str, ...]] = {}
        for event_type, raw_codes in raw_routes.items():
            if not isinstance(raw_codes, list) or not raw_codes:
                raise ValueError(f"event route {event_type} must contain modules.")
            event_routes[str(event_type).strip().upper()] = tuple(
                _module_identifier(str(code).strip().upper()) for code in raw_codes
            )
        if "REGULATORY_UPDATE" in event_routes:
            event_routes["REGULATORY_CHANGE"] = event_routes["REGULATORY_UPDATE"]
        return event_routes

    @staticmethod
    def _load_canonical_aliases(config_path: Path) -> dict[str, str]:
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
        aliases: dict[str, str] = {}
        for tickers in raw_config.values():
            if not isinstance(tickers, list):
                continue
            for raw_ticker in tickers:
                canonical = str(raw_ticker).strip().upper()
                for alias in TelemetryRouter._ticker_aliases(canonical):
                    aliases[alias] = canonical
        return aliases

    def _canonical_ticker(self, ticker: str) -> str:
        for alias in self._ticker_aliases(ticker):
            if alias in self._enterprise_layers:
                return self._canonical_aliases.get(alias, alias)
        return self._ticker_aliases(ticker)[0]

    def route(self, ticker: str, market_event: str | None = None) -> dict:
        normalized = self._canonical_ticker(ticker)
        if not normalized:
            raise ValueError("ticker must be a non-empty string.")

        event_type = (
            None
            if market_event is None
            else str(market_event).strip().upper()
        )
        if event_type:
            event_modules = self._event_routes.get(event_type)
            if event_modules is None:
                raise ValueError(f"Unknown market_event: {market_event}")
            layer = self._enterprise_layers.get(
                normalized,
                self._DEFAULT_ROUTE.target_infrastructure_layer,
            )
            priority = EVENT_PRIORITIES.get(event_type, "EVENT_DRIVEN_SURVEILLANCE")
            spec = RoutingSpec(
                ticker=normalized,
                target_infrastructure_layer=layer,
                triggered_kernels=event_modules,
                priority_level=priority,
                telemetry_hook=f"EXEC_{normalized}_{event_type}",
            )
            payload = asdict(spec)
            payload["triggered_kernels"] = list(spec.triggered_kernels)
            payload["market_event"] = event_type
            return payload

        spec = self._ROUTES.get(normalized)
        if spec is None:
            layer = self._enterprise_layers.get(normalized)
            if layer:
                spec = RoutingSpec(
                    ticker=normalized,
                    target_infrastructure_layer=layer,
                    triggered_kernels=LAYER_KERNELS[layer],
                    priority_level=LAYER_PRIORITIES[layer],
                    telemetry_hook=f"TARGET_ENTERPRISE_{normalized}_DAILY_LOOP",
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
        payload["market_event"] = "ROUTINE"
        return payload


def _module_identifier(code: str) -> str:
    from src.module_manifest import MODULE_SPECS

    for specification in MODULE_SPECS:
        if specification.code == code:
            return f"Module_{specification.module_id:02d}_{code}"
    raise ValueError(f"Unknown module code in event policy: {code}")


def route_ticker(ticker: str, market_event: str | None = None) -> dict:
    return TelemetryRouter().route(ticker, market_event=market_event)


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", nargs="?", default="NVDA")
    parser.add_argument("--event", dest="market_event")
    arguments = parser.parse_args()
    print(
        json.dumps(
            route_ticker(arguments.ticker, market_event=arguments.market_event),
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
