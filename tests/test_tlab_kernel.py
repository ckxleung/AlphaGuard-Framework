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


GENERATED_CODE = """
import time
import requests


API_VERSION = "2026-06-01"


def run_client(api_key, user_input):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-API-Version": API_VERSION,
    }
    payload = {"model": "gpt-5.4", "input": user_input}
    for attempt in range(3):
        try:
            response = requests.post(
                "https://api.vendor.example/v1/responses",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if response.status_code == 429:
                time.sleep(int(response.headers.get("Retry-After", "1")))
                continue
            response.raise_for_status()
            return response.json()["output_text"]
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(1)
"""


class ApiTelemetryAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        from evaluation_kernels.layer_1_telemetry.Module_06_TLAB.tlab_auditor import (
            ApiTelemetryAuditor,
        )

        self.auditor = ApiTelemetryAuditor()
        self.ground_truth = {
            "api_schema": {
                "api_version": "2026-06-01",
                "endpoint": "/v1/responses",
                "method": "POST",
                "required_payload_fields": ["model", "input"],
                "required_response_fields": ["output_text"],
            },
            "breaking_change_manifest": {
                "deprecated_versions": ["2025-01-01"],
                "removed_endpoints": ["/v1/completions"],
            },
            "required_headers": [
                "Authorization",
                "Content-Type",
                "X-API-Version",
            ],
            "rate_limit_policy": {
                "requires_429_retry": True,
                "retry_after_header": "Retry-After",
                "min_retry_attempts": 3,
            },
            "mandatory_tool_steps": [
                {
                    "step_id": "extract",
                    "tool_name": "extract_filing",
                    "required_output_keys": ["filing_id"],
                },
                {
                    "step_id": "search",
                    "tool_name": "search_filings",
                    "required_output_keys": ["matches"],
                },
                {
                    "step_id": "calculate",
                    "tool_name": "calculate_metric",
                    "required_output_keys": ["metric_value"],
                    "expected_numeric_output": 42.0,
                    "numeric_tolerance": 0.001,
                },
            ],
            "source_id": "DOC-SYNTHETIC-ALPHAGUARD-001",
        }

    def valid_ai_output(self) -> dict:
        return {
            "generated_code": GENERATED_CODE,
            "declared_api_version": "2026-06-01",
            "execution_trace": [
                {
                    "step_id": "extract",
                    "tool_name": "extract_filing",
                    "status": "SUCCESS",
                    "output": {"filing_id": "10-K-001"},
                },
                {
                    "step_id": "search",
                    "tool_name": "search_filings",
                    "status": "SUCCESS",
                    "output": {"matches": ["note-7"]},
                },
                {
                    "step_id": "calculate",
                    "tool_name": "calculate_metric",
                    "status": "SUCCESS",
                    "output": {"metric_value": 42.0004},
                },
            ],
        }

    def test_approves_code_schema_and_trace_contract(self) -> None:
        scorecard = self.auditor.execute_audit(
            self.valid_ai_output(),
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)
        self.assertEqual(scorecard["schema_violations"], [])
        self.assertEqual(scorecard["missing_execution_steps"], [])
        self.assertEqual(scorecard["breaking_change_exposure"], [])
        self.assertEqual(scorecard["instruction_following_score"], 1.0)

    def test_rejects_incompatible_version_endpoint_and_payload(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["declared_api_version"] = "2025-01-01"
        ai_output["generated_code"] = GENERATED_CODE.replace(
            "/v1/responses",
            "/v1/completions",
        ).replace('"input": user_input', '"prompt": user_input')

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("api_version", scorecard["schema_violations"])
        self.assertIn("endpoint", scorecard["schema_violations"])
        self.assertIn("payload.input", scorecard["schema_violations"])
        self.assertIn("deprecated_api_version", scorecard["breaking_change_exposure"])
        self.assertIn("removed_endpoint", scorecard["breaking_change_exposure"])

    def test_rejects_missing_auth_rate_limit_and_error_handling(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["generated_code"] = """
import requests

def run_client(user_input):
    payload = {"model": "gpt-5.4", "input": user_input}
    response = requests.post("https://api.vendor.example/v1/responses", json=payload)
    return response.json()["output_text"]
"""

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("header.Authorization", scorecard["schema_violations"])
        self.assertIn("rate_limit_retry", scorecard["schema_violations"])
        self.assertIn("error_handling", scorecard["schema_violations"])

    def test_rejects_missing_and_out_of_order_tool_steps(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["execution_trace"] = [
            ai_output["execution_trace"][1],
            ai_output["execution_trace"][0],
        ]

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("calculate", scorecard["missing_execution_steps"])
        self.assertFalse(scorecard["trace_order_valid"])

    def test_rejects_fabricated_success_and_bad_numeric_output(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["execution_trace"].append(
            {
                "step_id": "invented",
                "tool_name": "unknown_tool",
                "status": "SUCCESS",
                "output": {"ok": True},
            }
        )
        ai_output["execution_trace"][2]["output"]["metric_value"] = 41.0

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("invented", scorecard["fabricated_tool_successes"])
        self.assertIn("calculate.metric_value", scorecard["schema_violations"])

    def test_fails_closed_on_invalid_code_and_missing_source(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["generated_code"] = "def broken(:"
        with self.assertRaisesRegex(ValueError, "parse"):
            self.auditor.execute_audit(ai_output, self.ground_truth)

        missing_source = copy.deepcopy(self.ground_truth)
        missing_source.pop("source_id")
        with self.assertRaisesRegex(ValueError, "source_id"):
            self.auditor.execute_audit(self.valid_ai_output(), missing_source)

    def test_inputs_are_not_mutated(self) -> None:
        ai_output = self.valid_ai_output()
        ground_truth = copy.deepcopy(self.ground_truth)
        original_ai = copy.deepcopy(ai_output)
        original_truth = copy.deepcopy(ground_truth)

        self.auditor.execute_audit(ai_output, ground_truth)

        self.assertEqual(ai_output, original_ai)
        self.assertEqual(ground_truth, original_truth)


class ApiTelemetryAuditorIntegrationTests(unittest.TestCase):
    def test_manifest_registers_tlab_as_implemented(self) -> None:
        from src.module_manifest import get_module_spec

        specification = get_module_spec(6)
        self.assertEqual(specification.status, "IMPLEMENTED")
        self.assertEqual(specification.class_name, "ApiTelemetryAuditor")
        self.assertTrue(specification.implementation_path.endswith("tlab_auditor.py"))

    def test_tlab_runs_as_standalone_json_cli(self) -> None:
        auditor_tests = ApiTelemetryAuditorTests()
        auditor_tests.setUp()
        ai_output = auditor_tests.valid_ai_output()
        ground_truth = auditor_tests.ground_truth

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            ai_path = temporary / "ai_output.json"
            truth_path = temporary / "ground_truth.json"
            ai_path.write_text(json.dumps(ai_output), encoding="utf-8")
            truth_path.write_text(json.dumps(ground_truth), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        ROOT
                        / "evaluation_kernels"
                        / "layer_1_telemetry"
                        / "Module_06_TLAB"
                        / "tlab_auditor.py"
                    ),
                    "--ai-output",
                    str(ai_path),
                    "--ground-truth",
                    str(truth_path),
                ],
                cwd=ROOT.parent,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        scorecard = json.loads(result.stdout)
        self.assertEqual(scorecard["data_quality_status"], "APPROVED")


if __name__ == "__main__":
    unittest.main()
