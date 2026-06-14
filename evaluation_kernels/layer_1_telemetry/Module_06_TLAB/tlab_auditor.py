# -*- coding: utf-8 -*-
"""Audit generated API integrations and chained execution traces."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor


class ApiTelemetryAuditor(BaseAuditor):
    """Validate generated API code against one versioned telemetry contract."""

    @staticmethod
    def _text(payload: Mapping[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} is required and must be non-empty text.")
        return value.strip()

    @staticmethod
    def _text_list(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
        raw_values = payload.get(key)
        if not isinstance(raw_values, list):
            raise TypeError(f"{key} must be a list.")
        values: list[str] = []
        for index, value in enumerate(raw_values):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{key}[{index}] must be non-empty text.")
            values.append(value.strip())
        if len(values) != len(set(values)):
            raise ValueError(f"{key} cannot contain duplicate values.")
        return tuple(values)

    @staticmethod
    def _number(
        payload: Mapping[str, Any],
        key: str,
        *,
        default: float | None = None,
        non_negative: bool = True,
    ) -> float:
        if key not in payload:
            if default is None:
                raise ValueError(f"{key} is required.")
            return default
        value = payload[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{key} must be numeric.")
        number = float(value)
        if non_negative and number < 0.0:
            raise ValueError(f"{key} must be non-negative.")
        return number

    @classmethod
    def _api_schema(cls, truth: Mapping[str, Any]) -> dict[str, Any]:
        schema = truth.get("api_schema")
        if not isinstance(schema, Mapping):
            raise TypeError("api_schema must be an object.")
        method = cls._text(schema, "method").upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("api_schema.method is unsupported.")
        return {
            "api_version": cls._text(schema, "api_version"),
            "endpoint": cls._text(schema, "endpoint"),
            "method": method,
            "required_payload_fields": cls._text_list(
                schema,
                "required_payload_fields",
            ),
            "required_response_fields": cls._text_list(
                schema,
                "required_response_fields",
            ),
        }

    @classmethod
    def _breaking_changes(cls, truth: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
        manifest = truth.get("breaking_change_manifest")
        if not isinstance(manifest, Mapping):
            raise TypeError("breaking_change_manifest must be an object.")
        return {
            "deprecated_versions": cls._text_list(
                manifest,
                "deprecated_versions",
            ),
            "removed_endpoints": cls._text_list(manifest, "removed_endpoints"),
        }

    @classmethod
    def _rate_limit_policy(cls, truth: Mapping[str, Any]) -> dict[str, Any]:
        policy = truth.get("rate_limit_policy")
        if not isinstance(policy, Mapping):
            raise TypeError("rate_limit_policy must be an object.")
        requires_retry = policy.get("requires_429_retry")
        if not isinstance(requires_retry, bool):
            raise TypeError("rate_limit_policy.requires_429_retry must be boolean.")
        min_attempts = cls._number(
            policy,
            "min_retry_attempts",
            default=1.0,
            non_negative=True,
        )
        if min_attempts < 1:
            raise ValueError("rate_limit_policy.min_retry_attempts must be >= 1.")
        return {
            "requires_429_retry": requires_retry,
            "retry_after_header": cls._text(policy, "retry_after_header"),
            "min_retry_attempts": int(min_attempts),
        }

    @classmethod
    def _mandatory_steps(cls, truth: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
        raw_steps = truth.get("mandatory_tool_steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("mandatory_tool_steps must be a non-empty list.")
        steps: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, step in enumerate(raw_steps):
            if not isinstance(step, Mapping):
                raise TypeError(f"mandatory_tool_steps[{index}] must be an object.")
            step_id = cls._text(step, "step_id")
            if step_id in seen:
                raise ValueError("mandatory_tool_steps cannot duplicate step_id.")
            seen.add(step_id)
            normalized = {
                "step_id": step_id,
                "tool_name": cls._text(step, "tool_name"),
                "required_output_keys": cls._text_list(
                    step,
                    "required_output_keys",
                ),
            }
            if "expected_numeric_output" in step:
                normalized["expected_numeric_output"] = cls._number(
                    step,
                    "expected_numeric_output",
                    non_negative=False,
                )
                normalized["numeric_tolerance"] = cls._number(
                    step,
                    "numeric_tolerance",
                    default=0.0,
                )
            steps.append(normalized)
        return tuple(steps)

    @staticmethod
    def _parse_python(source: str) -> tuple[ast.AST, tuple[str, ...]]:
        try:
            tree = ast.parse(source)
        except SyntaxError as error:
            raise ValueError("generated_code must parse as Python.") from error
        constants: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                constants.append(node.value)
        return tree, tuple(constants)

    @staticmethod
    def _has_method_call(tree: ast.AST, method: str) -> bool:
        target = method.lower()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr.lower() == target:
                    return True
        return False

    @staticmethod
    def _has_try_except(tree: ast.AST) -> bool:
        return any(isinstance(node, ast.Try) and node.handlers for node in ast.walk(tree))

    @staticmethod
    def _max_range_constant(tree: ast.AST) -> int:
        max_attempts = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "range":
                continue
            if not node.args:
                continue
            argument = node.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, int):
                max_attempts = max(max_attempts, argument.value)
        return max_attempts

    @classmethod
    def _trace_report(
        cls,
        ai_data: Mapping[str, Any],
        mandatory_steps: tuple[dict[str, Any], ...],
    ) -> dict[str, Any]:
        execution_trace = ai_data.get("execution_trace")
        if not isinstance(execution_trace, list):
            raise TypeError("execution_trace must be a list.")
        expected_by_step = {step["step_id"]: step for step in mandatory_steps}
        allowed_tool_names = {step["tool_name"] for step in mandatory_steps}
        seen_steps: dict[str, Mapping[str, Any]] = {}
        fabricated_successes: list[str] = []
        actual_order: list[str] = []
        schema_violations: list[str] = []

        for index, raw_step in enumerate(execution_trace):
            if not isinstance(raw_step, Mapping):
                raise TypeError(f"execution_trace[{index}] must be an object.")
            step_id = cls._text(raw_step, "step_id")
            tool_name = cls._text(raw_step, "tool_name")
            status = cls._text(raw_step, "status").upper()
            output = raw_step.get("output")
            if not isinstance(output, Mapping):
                raise TypeError(f"execution_trace[{index}].output must be an object.")
            actual_order.append(step_id)
            if status == "SUCCESS" and (
                step_id not in expected_by_step or tool_name not in allowed_tool_names
            ):
                fabricated_successes.append(step_id)
            if step_id in expected_by_step and tool_name == expected_by_step[step_id]["tool_name"]:
                seen_steps[step_id] = raw_step

        missing_steps: list[str] = []
        for step in mandatory_steps:
            step_id = step["step_id"]
            observed = seen_steps.get(step_id)
            if observed is None:
                missing_steps.append(step_id)
                continue
            output = observed["output"]
            for key in step["required_output_keys"]:
                if key not in output:
                    schema_violations.append(f"{step_id}.{key}")
            if "expected_numeric_output" in step:
                value = output.get("metric_value")
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    schema_violations.append(f"{step_id}.metric_value")
                    continue
                delta = abs(float(value) - float(step["expected_numeric_output"]))
                if delta > float(step["numeric_tolerance"]):
                    schema_violations.append(f"{step_id}.metric_value")

        expected_order = [step["step_id"] for step in mandatory_steps]
        observed_mandatory_order = [
            step_id for step_id in actual_order if step_id in expected_by_step
        ]
        trace_order_valid = observed_mandatory_order == expected_order
        return {
            "missing_execution_steps": missing_steps,
            "fabricated_tool_successes": fabricated_successes,
            "trace_order_valid": trace_order_valid,
            "trace_schema_violations": schema_violations,
        }

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        api_schema = self._api_schema(truth)
        breaking_changes = self._breaking_changes(truth)
        required_headers = self._text_list(truth, "required_headers")
        rate_limit_policy = self._rate_limit_policy(truth)
        mandatory_steps = self._mandatory_steps(truth)
        source_id = self._text(truth, "source_id")
        generated_code = self._text(ai_data, "generated_code")
        declared_api_version = self._text(ai_data, "declared_api_version")
        tree, constants = self._parse_python(generated_code)
        constants_blob = "\n".join(constants)

        schema_violations: list[str] = []
        breaking_change_exposure: list[str] = []
        if declared_api_version != api_schema["api_version"]:
            schema_violations.append("api_version")
        if declared_api_version in breaking_changes["deprecated_versions"]:
            breaking_change_exposure.append("deprecated_api_version")
        if api_schema["endpoint"] not in constants_blob:
            schema_violations.append("endpoint")
        for removed_endpoint in breaking_changes["removed_endpoints"]:
            if removed_endpoint in constants_blob:
                breaking_change_exposure.append("removed_endpoint")
        if not self._has_method_call(tree, api_schema["method"]):
            schema_violations.append("method")
        for field in api_schema["required_payload_fields"]:
            if field not in constants:
                schema_violations.append(f"payload.{field}")
        for field in api_schema["required_response_fields"]:
            if field not in constants:
                schema_violations.append(f"response.{field}")
        for header in required_headers:
            if header not in constants:
                schema_violations.append(f"header.{header}")
        if rate_limit_policy["requires_429_retry"]:
            has_429 = "429" in generated_code
            has_retry_after = rate_limit_policy["retry_after_header"] in constants
            has_attempts = (
                self._max_range_constant(tree)
                >= rate_limit_policy["min_retry_attempts"]
            )
            if not (has_429 and has_retry_after and has_attempts):
                schema_violations.append("rate_limit_retry")
        if not self._has_try_except(tree):
            schema_violations.append("error_handling")

        trace_report = self._trace_report(ai_data, mandatory_steps)
        schema_violations.extend(trace_report["trace_schema_violations"])
        schema_violations = sorted(set(schema_violations))
        breaking_change_exposure = sorted(set(breaking_change_exposure))

        approved = (
            not schema_violations
            and not breaking_change_exposure
            and not trace_report["missing_execution_steps"]
            and not trace_report["fabricated_tool_successes"]
            and trace_report["trace_order_valid"]
        )
        if approved:
            rigor_score = 5.0
            feedback = (
                "APPROVED: generated API integration and chained execution trace "
                "match the versioned technical contract."
            )
        elif breaking_change_exposure:
            rigor_score = 1.0
            feedback = (
                "REJECTED: generated integration is exposed to a declared breaking "
                "API change."
            )
        elif schema_violations:
            rigor_score = 2.0
            feedback = (
                "REJECTED: generated integration violates the API schema or "
                "execution-output contract."
            )
        else:
            rigor_score = 2.5
            feedback = (
                "REJECTED: mandatory tool execution order or trace integrity failed."
            )

        total_checks = (
            len(api_schema["required_payload_fields"])
            + len(api_schema["required_response_fields"])
            + len(required_headers)
            + len(mandatory_steps)
            + 5
        )
        failed_checks = (
            len(schema_violations)
            + len(breaking_change_exposure)
            + len(trace_report["missing_execution_steps"])
            + len(trace_report["fabricated_tool_successes"])
            + (0 if trace_report["trace_order_valid"] else 1)
        )
        instruction_score = max(
            0.0,
            round((total_checks - failed_checks) / max(total_checks, 1), 4),
        )
        scorecard = self.build_scorecard(
            rigor_score=rigor_score,
            approved=approved,
            feedback=feedback,
            evidence={
                "source_id": source_id,
                "api_version": api_schema["api_version"],
                "endpoint": api_schema["endpoint"],
                "method": api_schema["method"],
                "required_headers": list(required_headers),
                "mandatory_step_count": len(mandatory_steps),
            },
        )
        scorecard.update(
            {
                "schema_violations": schema_violations,
                "missing_execution_steps": trace_report["missing_execution_steps"],
                "breaking_change_exposure": breaking_change_exposure,
                "fabricated_tool_successes": trace_report["fabricated_tool_successes"],
                "trace_order_valid": trace_report["trace_order_valid"],
                "instruction_following_score": instruction_score,
            }
        )
        return scorecard


def _load_json_object(path: Path) -> dict[str, Any]:  # pragma: no cover
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-output", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, required=True)
    arguments = parser.parse_args()
    result = ApiTelemetryAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
