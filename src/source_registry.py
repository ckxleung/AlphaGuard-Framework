# -*- coding: utf-8 -*-
"""Validate and resolve registered source-document snapshots."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


REGISTRY_VERSION = "1.0"
DEFAULT_REGISTRY_PATH = ROOT / "config" / "source_registry.json"
DOCUMENT_TYPES = frozenset(
    {
        "REGULATORY_FILING",
        "EXCHANGE_DISCLOSURE",
        "COMPANY_IR",
        "OFFICIAL_DATASET",
        "MARKET_DATA",
        "RESEARCH",
        "SOCIAL_MEDIA",
        "INTERNAL_FIXTURE",
    }
)
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
REGISTRY_FIELDS = frozenset({"registry_version", "generated_at", "documents"})
DOCUMENT_FIELDS = frozenset(
    {
        "document_id",
        "publisher",
        "title",
        "document_type",
        "jurisdiction",
        "publication_date",
        "canonical_url",
        "retrieved_at",
        "content_hash",
        "language",
        "primary_source",
        "local_path",
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


def _parse_date(value: Any, field_name: str) -> date:
    text = _require_text(value, field_name)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"{field_name} must use ISO-8601 YYYY-MM-DD.") from error
    if parsed.isoformat() != text:
        raise ValueError(f"{field_name} must use ISO-8601 YYYY-MM-DD.")
    return parsed


def _validate_local_snapshot(
    document: Mapping[str, Any],
    *,
    root: Path,
) -> None:
    local_path = document.get("local_path")
    if local_path is None:
        return
    normalized_path = _require_text(local_path, "local_path")
    candidate = Path(normalized_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("local_path must be a repository-relative path.")
    snapshot_path = root / candidate
    if not snapshot_path.is_file():
        raise ValueError(f"Registered local snapshot is missing: {normalized_path}")
    digest = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    if document["content_hash"] != f"sha256:{digest}":
        raise ValueError(
            f"content_hash does not match registered local snapshot: {normalized_path}"
        )


def validate_source_registry(
    registry: Mapping[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Validate and copy a source registry without mutating the caller."""
    if not isinstance(registry, Mapping):
        raise TypeError("source registry must be an object.")
    validated = copy.deepcopy(dict(registry))
    unknown_registry_fields = set(validated).difference(REGISTRY_FIELDS)
    if unknown_registry_fields:
        raise ValueError(
            "source registry contains unknown field(s): "
            + ", ".join(sorted(unknown_registry_fields))
        )
    if validated.get("registry_version") != REGISTRY_VERSION:
        raise ValueError(f"registry_version must be {REGISTRY_VERSION}.")
    _parse_timestamp(validated.get("generated_at"), "generated_at")

    documents = validated.get("documents")
    if not isinstance(documents, list) or not documents:
        raise ValueError("documents must be a non-empty list.")

    document_ids: set[str] = set()
    normalized_documents: list[dict[str, Any]] = []
    for index, document in enumerate(documents):
        if not isinstance(document, Mapping):
            raise TypeError(f"documents[{index}] must be an object.")
        normalized = dict(document)
        unknown_document_fields = set(normalized).difference(DOCUMENT_FIELDS)
        if unknown_document_fields:
            raise ValueError(
                f"documents[{index}] contains unknown field(s): "
                + ", ".join(sorted(unknown_document_fields))
            )
        document_id = _require_text(
            normalized.get("document_id"),
            f"documents[{index}].document_id",
        )
        if document_id in document_ids:
            raise ValueError(f"Duplicate document_id: {document_id}")
        document_ids.add(document_id)
        normalized["document_id"] = document_id

        for field_name in (
            "publisher",
            "title",
            "jurisdiction",
            "language",
        ):
            normalized[field_name] = _require_text(
                normalized.get(field_name),
                f"{document_id}.{field_name}",
            )

        document_type = _require_text(
            normalized.get("document_type"),
            f"{document_id}.document_type",
        )
        if document_type not in DOCUMENT_TYPES:
            raise ValueError(
                f"{document_id}.document_type is not an approved source type."
            )
        normalized["document_type"] = document_type
        publication_date = _parse_date(
            normalized.get("publication_date"),
            f"{document_id}.publication_date",
        )
        canonical_url = _require_text(
            normalized.get("canonical_url"),
            f"{document_id}.canonical_url",
        )
        if not canonical_url.startswith(("https://", "http://")):
            raise ValueError(f"{document_id}.canonical_url must use HTTP(S).")
        normalized["canonical_url"] = canonical_url
        retrieved_at = _parse_timestamp(
            normalized.get("retrieved_at"),
            f"{document_id}.retrieved_at",
        )
        if retrieved_at.date() < publication_date:
            raise ValueError(
                f"{document_id}.retrieved_at cannot precede publication_date."
            )
        content_hash = _require_text(
            normalized.get("content_hash"),
            f"{document_id}.content_hash",
        ).lower()
        if not SHA256_PATTERN.fullmatch(content_hash):
            raise ValueError(
                f"{document_id}.content_hash must be sha256 plus 64 hex characters."
            )
        normalized["content_hash"] = content_hash
        if not isinstance(normalized.get("primary_source"), bool):
            raise TypeError(f"{document_id}.primary_source must be boolean.")
        if "local_path" in normalized:
            normalized["local_path"] = _require_text(
                normalized["local_path"],
                f"{document_id}.local_path",
            )
        _validate_local_snapshot(normalized, root=root)
        normalized_documents.append(normalized)

    validated["documents"] = normalized_documents
    return validated


@dataclass(frozen=True, slots=True)
class DocumentIndex:
    """Immutable document lookup built from a validated registry."""

    documents: Mapping[str, Mapping[str, Any]]

    def require(self, document_id: str) -> Mapping[str, Any]:
        normalized_id = _require_text(document_id, "registry_document_id")
        try:
            return self.documents[normalized_id]
        except KeyError as error:
            raise KeyError(
                f"Source document is not registered: {normalized_id}"
            ) from error


def build_document_index(registry: Mapping[str, Any]) -> DocumentIndex:
    """Build an immutable lookup from an already validated registry."""
    documents = {
        document["document_id"]: MappingProxyType(dict(document))
        for document in registry["documents"]
    }
    return DocumentIndex(MappingProxyType(documents))


def load_source_registry(
    path: Path = DEFAULT_REGISTRY_PATH,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Load and validate one JSON source registry."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return validate_source_registry(payload, root=root)


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "registry",
        type=Path,
        nargs="?",
        default=DEFAULT_REGISTRY_PATH,
    )
    arguments = parser.parse_args()
    try:
        validated = load_source_registry(arguments.registry)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, indent=2))
        return 1

    print(
        json.dumps(
            {
                "valid": True,
                "registry_version": validated["registry_version"],
                "documents": len(validated["documents"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
