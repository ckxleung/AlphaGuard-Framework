# -*- coding: utf-8 -*-
"""Evidence-aware cohort and event routing for the monitored enterprise portfolio."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.main_pipeline import run_module_payloads
from src.module_manifest import MODULE_SPECS
from src.source_registry import (
    build_document_index,
    load_source_registry,
    validate_source_registry,
)


PROFILE_CONFIG = ROOT / "config" / "enterprise_monitoring_profiles.json"
TARGET_CONFIG = ROOT / "config" / "target_enterprises.json"
POLICY_CONFIG = ROOT / "config" / "event_routing_policy.json"
VALID_COHORTS = frozenset(
    {
        "FOUNDATIONAL_API",
        "ENTERPRISE_FINTECH_AGENT",
        "COMPUTE_INFRASTRUCTURE",
    }
)
VALID_DATA_CLASSIFICATIONS = frozenset(
    {"PLANNING_ONLY", "SYNTHETIC", "PUBLIC_SOURCE"}
)


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Missing monitoring configuration: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON configuration: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _require_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be non-empty text.")
    return value.strip()


def _parse_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("observed_at must be a timezone-aware ISO-8601 timestamp.")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(
            "observed_at must be a timezone-aware ISO-8601 timestamp."
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("observed_at must include an explicit timezone.")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _ticker_aliases(ticker: str) -> tuple[str, ...]:
    normalized = str(ticker).strip().upper()
    aliases = [normalized]
    if normalized.endswith(".SH"):
        aliases.append(normalized[:-3] + ".SS")
    elif normalized.endswith(".SS"):
        aliases.append(normalized[:-3] + ".SH")
    return tuple(dict.fromkeys(aliases))


def load_enterprise_profiles(
    profile_path: Path = PROFILE_CONFIG,
    target_path: Path = TARGET_CONFIG,
) -> dict[str, dict[str, str]]:
    """Load immutable cohort profiles and reconcile them to the target universe."""
    profile_config = _load_json_object(profile_path)
    target_config = _load_json_object(target_path)
    cohorts = profile_config.get("cohorts")
    if not isinstance(cohorts, dict) or set(cohorts) != VALID_COHORTS:
        raise ValueError("enterprise profiles must define the three canonical cohorts.")

    profiles: dict[str, dict[str, str]] = {}
    for cohort, cohort_payload in cohorts.items():
        if not isinstance(cohort_payload, dict):
            raise TypeError(f"cohort {cohort} must be an object.")
        description = _require_text(cohort_payload, "description")
        preferred_event_types = cohort_payload.get("preferred_event_types")
        if (
            not isinstance(preferred_event_types, list)
            or not preferred_event_types
            or any(
                not isinstance(event_type, str) or not event_type.strip()
                for event_type in preferred_event_types
            )
        ):
            raise ValueError(
                f"cohort {cohort} must define preferred_event_types."
            )
        normalized_event_types = [
            event_type.strip().upper() for event_type in preferred_event_types
        ]
        if len(normalized_event_types) != len(set(normalized_event_types)):
            raise ValueError(
                f"cohort {cohort} contains duplicate preferred event types."
            )
        tickers = cohort_payload.get("tickers")
        if not isinstance(tickers, list) or not tickers:
            raise ValueError(f"cohort {cohort} must contain tickers.")
        for raw_ticker in tickers:
            ticker = str(raw_ticker).strip().upper()
            if not ticker:
                raise ValueError(f"cohort {cohort} contains a blank ticker.")
            if ticker in profiles:
                raise ValueError(f"ticker {ticker} appears in multiple cohorts.")
            profiles[ticker] = {
                "ticker": ticker,
                "cohort": cohort,
                "cohort_description": description,
                "preferred_event_types": normalized_event_types,
            }

    target_layers: dict[str, str] = {}
    target_tickers = set()
    for layer_name, tickers in target_config.items():
        if not isinstance(tickers, list):
            continue
        for raw_ticker in tickers:
            ticker = str(raw_ticker).strip().upper()
            target_tickers.add(ticker)
            for alias in _ticker_aliases(ticker):
                target_layers[alias] = str(layer_name)
    if set(profiles) != target_tickers or len(profiles) != len(target_tickers):
        raise ValueError(
            "enterprise monitoring profiles must exactly match the target ticker universe."
        )
    for ticker, profile in profiles.items():
        profile["functional_layer"] = target_layers[ticker]
    return profiles


def load_routing_policy(path: Path = POLICY_CONFIG) -> dict[str, tuple[str, ...]]:
    """Load and validate daily and event-driven module selections."""
    payload = _load_json_object(path)
    manifest_codes = {specification.code for specification in MODULE_SPECS}
    baseline = payload.get("daily_baseline_modules")
    event_routes = payload.get("event_routes")
    if not isinstance(baseline, list) or len(baseline) != 2:
        raise ValueError("daily_baseline_modules must contain exactly two modules.")
    if not isinstance(event_routes, dict) or not event_routes:
        raise ValueError("event_routes must be a non-empty object.")

    routes: dict[str, tuple[str, ...]] = {
        "DAILY_BASELINE": tuple(str(code).strip().upper() for code in baseline)
    }
    for event_type, raw_codes in event_routes.items():
        if not isinstance(raw_codes, list) or not 3 <= len(raw_codes) <= 5:
            raise ValueError(
                f"event route {event_type} must select between three and five modules."
            )
        routes[str(event_type).strip().upper()] = tuple(
            str(code).strip().upper() for code in raw_codes
        )

    for event_type, codes in routes.items():
        if len(codes) != len(set(codes)):
            raise ValueError(f"event route {event_type} contains duplicate modules.")
        unknown = set(codes).difference(manifest_codes)
        if unknown:
            raise ValueError(
                f"event route {event_type} references unknown module(s): "
                + ", ".join(sorted(unknown))
            )
    return routes


def _validate_event(
    event: Mapping[str, Any],
    source_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        raise TypeError("event must be an object.")
    event_id = _require_text(event, "event_id")
    ticker = _require_text(event, "ticker").upper()
    event_type = _require_text(event, "event_type").upper()
    observed_at = _parse_timestamp(event.get("observed_at"))
    data_classification = _require_text(event, "data_classification").upper()
    if data_classification not in VALID_DATA_CLASSIFICATIONS:
        raise ValueError(
            "data_classification must be PLANNING_ONLY, SYNTHETIC, or PUBLIC_SOURCE."
        )
    evidence_refs = event.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        raise TypeError("evidence_refs must be a list.")
    normalized_refs = []
    for reference in evidence_refs:
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("evidence_refs must contain non-empty text values.")
        normalized_refs.append(reference.strip())
    if len(normalized_refs) != len(set(normalized_refs)):
        raise ValueError("evidence_refs cannot contain duplicates.")
    if data_classification == "PLANNING_ONLY" and normalized_refs:
        raise ValueError("PLANNING_ONLY events cannot contain evidence_refs.")
    if normalized_refs:
        registry = (
            load_source_registry()
            if source_registry is None
            else validate_source_registry(source_registry)
        )
        document_index = build_document_index(registry)
        for reference in normalized_refs:
            try:
                document = document_index.require(reference)
            except KeyError as error:
                raise ValueError(
                    f"evidence_ref is not registered: {reference}"
                ) from error
            if (
                data_classification == "PUBLIC_SOURCE"
                and document["document_type"] == "INTERNAL_FIXTURE"
            ):
                raise ValueError(
                    "PUBLIC_SOURCE events cannot cite INTERNAL_FIXTURE documents."
                )
    return {
        "event_id": event_id,
        "ticker": ticker,
        "event_type": event_type,
        "observed_at": observed_at,
        "evidence_refs": normalized_refs,
        "data_classification": data_classification,
    }


def plan_monitoring_event(
    event: Mapping[str, Any],
    source_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a transparent module plan without claiming that an audit ran."""
    validated = _validate_event(event, source_registry)
    profiles = load_enterprise_profiles()
    profile = profiles.get(validated["ticker"])
    if profile is None:
        raise ValueError(
            f"ticker {validated['ticker']} is not in the monitored enterprise universe."
        )
    routes = load_routing_policy()
    selected = routes.get(validated["event_type"])
    if selected is None:
        raise ValueError(f"Unknown event_type: {validated['event_type']}")

    status_by_code = {
        specification.code: specification.status
        for specification in MODULE_SPECS
    }
    executable = [
        code for code in selected if status_by_code[code] == "IMPLEMENTED"
    ]
    unavailable = [
        code for code in selected if status_by_code[code] != "IMPLEMENTED"
    ]
    return {
        **validated,
        "cohort": profile["cohort"],
        "cohort_description": profile["cohort_description"],
        "target_infrastructure_layer": profile["functional_layer"],
        "cohort_event_priority": (
            "BASELINE"
            if validated["event_type"] == "DAILY_BASELINE"
            else (
                "PREFERRED"
                if validated["event_type"] in profile["preferred_event_types"]
                else "SECONDARY"
            )
        ),
        "selected_modules": list(selected),
        "executable_modules": executable,
        "unavailable_modules": unavailable,
        "execution_status": "PLANNED",
        "publication_eligible": False,
        "publication_blockers": [
            "No kernel scorecards have been produced.",
            *(
                ["Selected modules are not yet implemented: " + ", ".join(unavailable)]
                if unavailable
                else []
            ),
        ],
    }


def execute_monitoring_event(
    event: Mapping[str, Any],
    module_payloads: dict[str, Any],
    source_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute available selected kernels with per-module evidence payloads."""
    if not isinstance(module_payloads, dict):
        raise TypeError("module_payloads must be an object keyed by module code.")
    plan = plan_monitoring_event(event, source_registry)
    for code in plan["executable_modules"]:
        payload = module_payloads.get(code)
        if payload is None:
            continue
        if not isinstance(payload, Mapping):
            raise TypeError(f"module_payloads.{code} must be an object.")
        payload_classification = _require_text(
            payload,
            "data_classification",
        ).upper()
        if payload_classification != plan["data_classification"]:
            raise ValueError(
                f"module_payloads.{code}.data_classification must match the event."
            )
        payload_refs = payload.get("evidence_refs")
        if not isinstance(payload_refs, list) or not payload_refs:
            raise ValueError(
                f"module_payloads.{code}.evidence_refs must be a non-empty list."
            )
        normalized_payload_refs = {
            _require_text({"reference": reference}, "reference")
            for reference in payload_refs
        }
        if len(normalized_payload_refs) != len(payload_refs):
            raise ValueError(
                f"module_payloads.{code}.evidence_refs cannot contain duplicates."
            )
        unknown_refs = normalized_payload_refs.difference(plan["evidence_refs"])
        if unknown_refs:
            raise ValueError(
                f"module_payloads.{code} references evidence outside the event: "
                + ", ".join(sorted(unknown_refs))
            )
    execution = run_module_payloads(
        module_payloads,
        selected_codes=tuple(plan["executable_modules"]),
    )
    executed_codes = set(execution["results"])
    skipped = [
        code for code in plan["executable_modules"] if code not in executed_codes
    ]
    blockers = []
    if plan["unavailable_modules"]:
        blockers.append(
            "Selected modules are not yet implemented: "
            + ", ".join(plan["unavailable_modules"])
        )
    if skipped:
        blockers.append(
            "Executable modules are missing validated payloads: "
            + ", ".join(skipped)
        )
    if not plan["evidence_refs"]:
        blockers.append("No source evidence references were supplied.")
    if plan["data_classification"] != "PUBLIC_SOURCE":
        blockers.append(
            "Only PUBLIC_SOURCE runs can be considered for publication."
        )
    if not execution["results"]:
        blockers.append("No kernel scorecards were produced.")

    return {
        **plan,
        "execution_status": "EXECUTED" if execution["results"] else "NO_EXECUTION",
        "results": execution["results"],
        "executed_modules": list(execution["results"]),
        "skipped_executable_modules": skipped,
        "publication_eligible": not blockers,
        "publication_blockers": blockers,
    }


def plan_portfolio_baseline(observed_at: str) -> dict[str, Any]:
    """Build a planning-only daily baseline across all monitored targets."""
    profiles = load_enterprise_profiles()
    plans = [
        plan_monitoring_event(
            {
                "event_id": f"baseline-{ticker}-{observed_at[:10]}",
                "ticker": ticker,
                "event_type": "DAILY_BASELINE",
                "observed_at": observed_at,
                "evidence_refs": [],
                "data_classification": "PLANNING_ONLY",
            }
        )
        for ticker in sorted(profiles)
    ]
    return {
        "observed_at": _parse_timestamp(observed_at),
        "target_count": len(plans),
        "plans": plans,
        "publication_eligible": False,
        "disclosure": (
            "This is a routing plan only. It contains no live ingestion evidence "
            "and no completed audit scorecards."
        ),
    }


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--event", type=Path)
    group.add_argument("--portfolio-baseline", action="store_true")
    parser.add_argument(
        "--observed-at",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    parser.add_argument("--module-payloads", type=Path)
    arguments = parser.parse_args()

    try:
        if arguments.portfolio_baseline:
            report = plan_portfolio_baseline(arguments.observed_at)
        else:
            event = _load_json_object(arguments.event)
            if arguments.module_payloads:
                report = execute_monitoring_event(
                    event,
                    _load_json_object(arguments.module_payloads),
                )
            else:
                report = plan_monitoring_event(event)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, indent=2))
        return 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
