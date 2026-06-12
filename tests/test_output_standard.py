from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def valid_artifact() -> dict:
    return {
        "schema_version": "1.0",
        "artifact_id": "CAD-TN-20260612-001",
        "document_type": "TELEMETRY_NOTE",
        "title": "Synthetic Enterprise AI Telemetry Note",
        "as_of": "2026-06-12T16:00:00+08:00",
        "generated_at": "2026-06-12T16:05:00+08:00",
        "engine_version": "AlphaGuard 1.0.4",
        "classification": "B2B_ENTERPRISE_AI_INFRASTRUCTURE_RISK",
        "executive_summary": (
            "Synthetic fixture demonstrating the publication contract."
        ),
        "claims": [
            {
                "claim_id": "CLM-001",
                "claim_type": "FACT",
                "statement": "The synthetic audit score is 2.1 out of 5.0.",
                "source_refs": ["SRC-001"],
                "methodology_refs": ["Module_15_SCGV"],
            },
            {
                "claim_id": "CLM-002",
                "claim_type": "INFERENCE",
                "statement": "The synthetic result indicates elevated model risk.",
                "source_refs": ["SRC-001"],
                "methodology_refs": ["Module_15_SCGV"],
            },
        ],
        "sources": [
            {
                "source_id": "SRC-001",
                "title": "Synthetic AlphaGuard Fixture",
                "url": "https://example.com/alphaguard-fixture",
                "accessed_at": "2026-06-12T15:55:00+08:00",
            }
        ],
        "scorecards": [
            {
                "kernel_id": "Module_15_SCGV",
                "target": "SYNTHETIC",
                "rigor_score": 2.1,
                "data_quality_status": "REJECTED",
                "structured_written_feedback": (
                    "Synthetic fixture rejected by the dual-variance rule."
                ),
            }
        ],
        "disclosures": {
            "informational_only": True,
            "independent_research": True,
            "derivatives_risk_disclosed": True,
            "synthetic_data": True,
        },
    }


class PublicationOutputContractTests(unittest.TestCase):
    def test_valid_publication_artifact_is_accepted_without_mutation(self) -> None:
        from src.output_standard import validate_publication_artifact

        artifact = valid_artifact()
        original = copy.deepcopy(artifact)

        validated = validate_publication_artifact(artifact)

        self.assertEqual(artifact, original)
        self.assertEqual(validated["artifact_id"], "CAD-TN-20260612-001")
        self.assertIsNot(validated, artifact)

    def test_fact_claim_without_source_is_rejected(self) -> None:
        from src.output_standard import validate_publication_artifact

        artifact = valid_artifact()
        artifact["claims"][0]["source_refs"] = []

        with self.assertRaisesRegex(ValueError, "FACT.*source"):
            validate_publication_artifact(artifact)

    def test_inference_claim_without_source_is_rejected(self) -> None:
        from src.output_standard import validate_publication_artifact

        artifact = valid_artifact()
        artifact["claims"][1]["source_refs"] = []

        with self.assertRaisesRegex(ValueError, "INFERENCE.*source"):
            validate_publication_artifact(artifact)

    def test_unknown_source_reference_is_rejected(self) -> None:
        from src.output_standard import validate_publication_artifact

        artifact = valid_artifact()
        artifact["claims"][0]["source_refs"] = ["SRC-404"]

        with self.assertRaisesRegex(ValueError, "unknown source"):
            validate_publication_artifact(artifact)

    def test_timestamp_without_timezone_is_rejected(self) -> None:
        from src.output_standard import validate_publication_artifact

        artifact = valid_artifact()
        artifact["as_of"] = "2026-06-12T16:00:00"

        with self.assertRaisesRegex(ValueError, "timezone"):
            validate_publication_artifact(artifact)

    def test_invalid_scorecard_is_rejected(self) -> None:
        from src.output_standard import validate_publication_artifact

        artifact = valid_artifact()
        artifact["scorecards"][0]["rigor_score"] = 9.0

        with self.assertRaisesRegex(ValueError, "rigor_score"):
            validate_publication_artifact(artifact)

    def test_missing_disclosure_is_rejected(self) -> None:
        from src.output_standard import validate_publication_artifact

        artifact = valid_artifact()
        artifact["disclosures"]["informational_only"] = False

        with self.assertRaisesRegex(ValueError, "informational_only"):
            validate_publication_artifact(artifact)

    def test_publication_validator_runs_as_standalone_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "artifact.json"
            artifact_path.write_text(
                json.dumps(valid_artifact()),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "src" / "output_standard.py"),
                    str(artifact_path),
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
        self.assertEqual(payload["artifact_id"], "CAD-TN-20260612-001")


if __name__ == "__main__":
    unittest.main()
