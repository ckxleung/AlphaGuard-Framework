from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def valid_registry() -> dict:
    return {
        "registry_version": "1.0",
        "generated_at": "2026-06-13T10:00:00+08:00",
        "documents": [
            {
                "document_id": "DOC-SYNTHETIC-ALPHAGUARD-001",
                "publisher": "China Alpha Dispatch",
                "title": "Synthetic AlphaGuard Publication Fixture",
                "document_type": "INTERNAL_FIXTURE",
                "jurisdiction": "GLOBAL",
                "publication_date": "2026-06-12",
                "canonical_url": (
                    "https://github.com/ckxleung/AlphaGuard-Framework/"
                    "blob/main/examples/source_documents/"
                    "synthetic_publication_fixture.txt"
                ),
                "retrieved_at": "2026-06-12T15:55:00+08:00",
                "content_hash": (
                    "sha256:"
                    "ef7d4b727929c6555bd6f77036fb1817df5e35bf5cfb39"
                    "58aa5c2463b9071199"
                ),
                "language": "en",
                "primary_source": True,
            }
        ],
    }


class SourceRegistryTests(unittest.TestCase):
    def test_valid_registry_is_accepted_without_mutation(self) -> None:
        from src.source_registry import validate_source_registry

        registry = valid_registry()
        original = copy.deepcopy(registry)

        validated = validate_source_registry(registry)

        self.assertEqual(registry, original)
        self.assertEqual(
            validated["documents"][0]["document_id"],
            "DOC-SYNTHETIC-ALPHAGUARD-001",
        )

    def test_duplicate_document_id_is_rejected(self) -> None:
        from src.source_registry import validate_source_registry

        registry = valid_registry()
        registry["documents"].append(copy.deepcopy(registry["documents"][0]))

        with self.assertRaisesRegex(ValueError, "Duplicate document_id"):
            validate_source_registry(registry)

    def test_invalid_hash_is_rejected(self) -> None:
        from src.source_registry import validate_source_registry

        registry = valid_registry()
        registry["documents"][0]["content_hash"] = "sha256:not-a-hash"

        with self.assertRaisesRegex(ValueError, "content_hash"):
            validate_source_registry(registry)

    def test_retrieval_timestamp_requires_timezone(self) -> None:
        from src.source_registry import validate_source_registry

        registry = valid_registry()
        registry["documents"][0]["retrieved_at"] = "2026-06-12T15:55:00"

        with self.assertRaisesRegex(ValueError, "timezone"):
            validate_source_registry(registry)

    def test_retrieval_cannot_precede_publication(self) -> None:
        from src.source_registry import validate_source_registry

        registry = valid_registry()
        registry["documents"][0]["retrieved_at"] = "2026-06-11T23:59:00+08:00"

        with self.assertRaisesRegex(ValueError, "publication_date"):
            validate_source_registry(registry)

    def test_unknown_document_metadata_is_rejected(self) -> None:
        from src.source_registry import validate_source_registry

        registry = valid_registry()
        registry["documents"][0]["uncontrolled_note"] = "ambiguous"

        with self.assertRaisesRegex(ValueError, "unknown field"):
            validate_source_registry(registry)

    def test_registry_lookup_rejects_unknown_document(self) -> None:
        from src.source_registry import build_document_index, validate_source_registry

        index = build_document_index(validate_source_registry(valid_registry()))

        with self.assertRaisesRegex(KeyError, "DOC-UNKNOWN"):
            index.require("DOC-UNKNOWN")

    def test_repository_registry_runs_as_standalone_cli(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "src" / "source_registry.py"),
                str(ROOT / "config" / "source_registry.json"),
            ],
            cwd=ROOT.parent,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["valid"])
        self.assertGreaterEqual(payload["documents"], 1)


if __name__ == "__main__":
    unittest.main()
