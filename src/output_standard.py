# -*- coding: utf-8 -*-
"""Machine-verifiable publication contract for AlphaGuard research artifacts."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor
from src.market_clock import validate_timestamp_matrix
from src.source_registry import (
    DocumentIndex,
    build_document_index,
    load_source_registry,
    validate_source_registry,
)


SCHEMA_VERSION = "1.1"
DOCUMENT_TYPES = frozenset({"TELEMETRY_NOTE", "DEEP_DIVE_WHITEPAPER"})
CLAIM_TYPES = frozenset({"FACT", "INFERENCE", "SCENARIO"})
LOCATOR_TYPES = frozenset(
    {
        "PAGE",
        "SECTION",
        "TABLE",
        "EXHIBIT",
        "PARAGRAPH",
        "CELL_RANGE",
        "TIMESTAMP",
        "LINE_RANGE",
        "JSON_POINTER",
    }
)
REQUIRED_ARTIFACT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "document_type",
        "title",
        "as_of",
        "generated_at",
        "telemetry_timestamp_matrix",
        "engine_version",
        "classification",
        "executive_summary",
        "claims",
        "sources",
        "scorecards",
        "disclosures",
    }
)
REQUIRED_DISCLOSURES = frozenset(
    {
        "informational_only",
        "independent_research",
        "derivatives_risk_disclosed",
        "synthetic_data",
    }
)


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty text.")
    return value.strip()


def _parse_timestamp(value: Any, field_name: str) -> datetime:
    text = _require_text(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp.") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include an explicit timezone.")
    return parsed


def _validate_locator(locator: Any, source_id: str) -> dict[str, str]:
    if not isinstance(locator, Mapping):
        raise ValueError(f"Source {source_id} locator must be an object.")
    locator_type = _require_text(
        locator.get("type"),
        f"source {source_id} locator type",
    )
    if locator_type not in LOCATOR_TYPES:
        raise ValueError(
            f"Source {source_id} locator type is not supported."
        )
    return {
        "type": locator_type,
        "value": _require_text(
            locator.get("value"),
            f"source {source_id} locator value",
        ),
    }


def _validate_sources(
    sources: Any,
    document_index: DocumentIndex,
) -> tuple[list[dict[str, Any]], frozenset[str]]:
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources must be a non-empty list.")

    validated_sources: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            raise TypeError(f"sources[{index}] must be an object.")
        validated = dict(source)
        source_id = _require_text(validated.get("source_id"), "source_id")
        if source_id in source_ids:
            raise ValueError(f"Duplicate source_id: {source_id}")
        source_ids.add(source_id)
        validated["source_id"] = source_id
        registry_document_id = _require_text(
            validated.get("registry_document_id"),
            f"source {source_id} registry_document_id",
        )
        try:
            registered = document_index.require(registry_document_id)
        except KeyError as error:
            raise ValueError(
                f"Source document is not registered: {registry_document_id}"
            ) from error
        validated["registry_document_id"] = registry_document_id

        title = _require_text(validated.get("title"), "source title")
        if title != registered["title"]:
            raise ValueError(
                f"Source {source_id} title does not match the registered title."
            )
        validated["title"] = title
        url = _require_text(validated.get("url"), "source url")
        if not url.startswith(("https://", "http://")):
            raise ValueError(f"Source {source_id} must use an HTTP(S) URL.")
        if url != registered["canonical_url"]:
            raise ValueError(
                f"Source {source_id} URL does not match the registered URL."
            )
        validated["url"] = url
        accessed_at = _parse_timestamp(
            validated.get("accessed_at"),
            "source accessed_at",
        )
        registered_at = _parse_timestamp(
            registered["retrieved_at"],
            "registered source retrieved_at",
        )
        if accessed_at != registered_at:
            raise ValueError(
                f"Source {source_id} accessed_at does not match the registered snapshot."
            )
        content_hash = _require_text(
            validated.get("content_hash"),
            f"source {source_id} content_hash",
        ).lower()
        if content_hash != registered["content_hash"]:
            raise ValueError(
                f"Source {source_id} content_hash does not match the registered snapshot."
            )
        validated["content_hash"] = content_hash
        validated["locator"] = _validate_locator(
            validated.get("locator"),
            source_id,
        )
        validated_sources.append(validated)
    return validated_sources, frozenset(source_ids)


def _validate_claims(
    claims: Any,
    source_ids: frozenset[str],
) -> list[dict[str, Any]]:
    if not isinstance(claims, list) or not claims:
        raise ValueError("claims must be a non-empty list.")

    validated_claims: list[dict[str, Any]] = []
    claim_ids: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            raise TypeError(f"claims[{index}] must be an object.")
        validated = dict(claim)
        claim_id = _require_text(validated.get("claim_id"), "claim_id")
        if claim_id in claim_ids:
            raise ValueError(f"Duplicate claim_id: {claim_id}")
        claim_ids.add(claim_id)

        claim_type = _require_text(
            validated.get("claim_type"),
            f"claim {claim_id} claim_type",
        )
        if claim_type not in CLAIM_TYPES:
            raise ValueError(
                f"Claim {claim_id} claim_type must be FACT, INFERENCE, or SCENARIO."
            )
        validated["claim_id"] = claim_id
        validated["claim_type"] = claim_type
        validated["statement"] = _require_text(
            validated.get("statement"),
            f"claim {claim_id} statement",
        )

        source_refs = validated.get("source_refs")
        if not isinstance(source_refs, list):
            raise TypeError(f"Claim {claim_id} source_refs must be a list.")
        normalized_refs = [
            _require_text(reference, f"claim {claim_id} source reference")
            for reference in source_refs
        ]
        if claim_type in {"FACT", "INFERENCE"} and not normalized_refs:
            raise ValueError(
                f"{claim_type} claim {claim_id} must cite at least one source."
            )
        unknown_sources = set(normalized_refs).difference(source_ids)
        if unknown_sources:
            raise ValueError(
                f"Claim {claim_id} references unknown source(s): "
                + ", ".join(sorted(unknown_sources))
            )
        validated["source_refs"] = normalized_refs

        methodology_refs = validated.get("methodology_refs")
        if not isinstance(methodology_refs, list) or not methodology_refs:
            raise ValueError(
                f"Claim {claim_id} must cite at least one methodology reference."
            )
        validated["methodology_refs"] = [
            _require_text(reference, f"claim {claim_id} methodology reference")
            for reference in methodology_refs
        ]
        validated_claims.append(validated)
    return validated_claims


def _validate_scorecards(scorecards: Any) -> list[dict[str, Any]]:
    if not isinstance(scorecards, list) or not scorecards:
        raise ValueError("scorecards must be a non-empty list.")

    validated_scorecards: list[dict[str, Any]] = []
    for index, scorecard in enumerate(scorecards):
        if not isinstance(scorecard, Mapping):
            raise TypeError(f"scorecards[{index}] must be an object.")
        validated = BaseAuditor.validate_scorecard(scorecard)
        validated["kernel_id"] = _require_text(
            scorecard.get("kernel_id"),
            f"scorecards[{index}] kernel_id",
        )
        validated["target"] = _require_text(
            scorecard.get("target"),
            f"scorecards[{index}] target",
        )
        validated_scorecards.append(validated)
    return validated_scorecards


def _validate_disclosures(disclosures: Any) -> dict[str, bool]:
    if not isinstance(disclosures, Mapping):
        raise TypeError("disclosures must be an object.")
    missing = REQUIRED_DISCLOSURES.difference(disclosures)
    if missing:
        raise ValueError(
            "disclosures is missing required keys: " + ", ".join(sorted(missing))
        )

    validated: dict[str, bool] = {}
    for field_name in REQUIRED_DISCLOSURES:
        value = disclosures[field_name]
        if not isinstance(value, bool):
            raise TypeError(f"disclosures.{field_name} must be boolean.")
        validated[field_name] = value

    for required_true in (
        "informational_only",
        "independent_research",
        "derivatives_risk_disclosed",
    ):
        if not validated[required_true]:
            raise ValueError(f"disclosures.{required_true} must be true.")
    return validated


def validate_publication_artifact(
    artifact: Mapping[str, Any],
    source_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and copy a publication artifact without mutating the caller."""
    if not isinstance(artifact, Mapping):
        raise TypeError("publication artifact must be an object.")
    missing = REQUIRED_ARTIFACT_KEYS.difference(artifact)
    if missing:
        raise ValueError(
            "publication artifact is missing required keys: "
            + ", ".join(sorted(missing))
        )

    validated = copy.deepcopy(dict(artifact))
    if validated["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}.")

    validated["artifact_id"] = _require_text(
        validated["artifact_id"],
        "artifact_id",
    )
    document_type = _require_text(validated["document_type"], "document_type")
    if document_type not in DOCUMENT_TYPES:
        raise ValueError(
            "document_type must be TELEMETRY_NOTE or DEEP_DIVE_WHITEPAPER."
        )
    validated["document_type"] = document_type
    for field_name in (
        "title",
        "engine_version",
        "classification",
        "executive_summary",
    ):
        validated[field_name] = _require_text(validated[field_name], field_name)

    as_of = _parse_timestamp(validated["as_of"], "as_of")
    generated_at = _parse_timestamp(validated["generated_at"], "generated_at")
    if generated_at < as_of:
        raise ValueError("generated_at cannot precede as_of.")

    validated["telemetry_timestamp_matrix"] = validate_timestamp_matrix(
        validated["telemetry_timestamp_matrix"]
    )
    matrix_utc = datetime.fromisoformat(
        validated["telemetry_timestamp_matrix"]["telemetry_matrix_utc"].replace(
            "Z",
            "+00:00",
        )
    )
    if as_of != matrix_utc:
        raise ValueError("as_of must match the telemetry timestamp matrix instant.")

    registry = (
        load_source_registry()
        if source_registry is None
        else validate_source_registry(source_registry)
    )
    validated["sources"], source_ids = _validate_sources(
        validated["sources"],
        build_document_index(registry),
    )
    validated["claims"] = _validate_claims(validated["claims"], source_ids)
    validated["scorecards"] = _validate_scorecards(validated["scorecards"])
    validated["disclosures"] = _validate_disclosures(validated["disclosures"])
    return validated


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    arguments = parser.parse_args()
    try:
        payload = json.loads(arguments.artifact.read_text(encoding="utf-8"))
        validated = validate_publication_artifact(payload)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, indent=2))
        return 1

    print(
        json.dumps(
            {
                "valid": True,
                "artifact_id": validated["artifact_id"],
                "document_type": validated["document_type"],
                "claims": len(validated["claims"]),
                "sources": len(validated["sources"]),
                "scorecards": len(validated["scorecards"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
