# -*- coding: utf-8 -*-
"""Audit indirect-method operating cash flow statement articulation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor


class CorporateFinancialAuditor(BaseAuditor):
    """Enforce the indirect-method operating cash flow identity."""

    DEFAULT_ABSOLUTE_TOLERANCE = Decimal("0.01")
    DEFAULT_RELATIVE_TOLERANCE = Decimal("0.000001")

    @staticmethod
    def _text(payload: Mapping[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} is required and must be non-empty text.")
        return value.strip()

    @staticmethod
    def _decimal(
        payload: Mapping[str, Any],
        key: str,
        *,
        default: Decimal | None = None,
        non_negative: bool = False,
    ) -> Decimal:
        if key not in payload:
            if default is None:
                raise ValueError(f"{key} is required.")
            return default

        value = payload[key]
        if isinstance(value, bool):
            raise TypeError(f"{key} must be numeric.")
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise TypeError(f"{key} must be numeric.") from error
        if not number.is_finite():
            raise ValueError(f"{key} must be finite.")
        if non_negative and number < 0:
            raise ValueError(f"{key} must be non-negative.")
        return number

    @classmethod
    def _tolerance(
        cls,
        truth: Mapping[str, Any],
        expected_value: Decimal,
    ) -> Decimal:
        absolute_tolerance = cls._decimal(
            truth,
            "absolute_tolerance",
            default=cls.DEFAULT_ABSOLUTE_TOLERANCE,
            non_negative=True,
        )
        relative_tolerance = cls._decimal(
            truth,
            "relative_tolerance",
            default=cls.DEFAULT_RELATIVE_TOLERANCE,
            non_negative=True,
        )
        return max(absolute_tolerance, abs(expected_value) * relative_tolerance)

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        if "change_in_working_capital" in truth:
            raise ValueError(
                "Use increase_in_net_working_capital with a positive value for "
                "cash absorbed by working capital; change_in_working_capital is "
                "sign-ambiguous."
            )

        net_income = self._decimal(truth, "net_income")
        non_cash_adjustments = self._decimal(truth, "non_cash_adjustments")
        increase_in_nwc = self._decimal(
            truth,
            "increase_in_net_working_capital",
        )
        reported_ocf = self._decimal(
            truth,
            "reported_operating_cash_flow",
        )
        ai_reported_ocf = self._decimal(
            ai_data,
            "reported_operating_cash_flow",
        )
        currency = str(truth.get("currency", "")).strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter alphabetic code.")
        source_id = self._text(truth, "source_id")
        fiscal_period_end = self._text(truth, "fiscal_period_end")
        try:
            date.fromisoformat(fiscal_period_end)
        except ValueError as error:
            raise ValueError(
                "fiscal_period_end must use ISO-8601 YYYY-MM-DD format."
            ) from error

        formula_ocf = net_income + non_cash_adjustments - increase_in_nwc
        tolerance = self._tolerance(truth, formula_ocf)
        ground_truth_deviation = abs(reported_ocf - formula_ocf)
        if ground_truth_deviation > tolerance:
            raise ValueError(
                "reported ground truth operating cash flow does not reconcile "
                "to net income + non-cash adjustments - increase in net working "
                "capital within tolerance."
            )

        ai_deviation = abs(ai_reported_ocf - formula_ocf)
        sign_inversion_ocf = net_income + non_cash_adjustments + increase_in_nwc
        sign_inversion_detected = (
            increase_in_nwc != 0
            and abs(ai_reported_ocf - sign_inversion_ocf) <= tolerance
        )
        approved = ai_deviation <= tolerance and not sign_inversion_detected

        if approved:
            rigor_score = 5.0
            feedback = (
                "APPROVED: AI-reported operating cash flow reconciles to the "
                "indirect-method identity within the declared tolerance."
            )
            anomalies: list[str] = []
        elif sign_inversion_detected:
            rigor_score = 1.0
            feedback = (
                "REJECTED: working-capital sign inversion detected. The AI added "
                "an increase in net working capital instead of subtracting the "
                "cash absorbed by that increase."
            )
            anomalies = [
                "Working-capital sign inversion in the indirect-method OCF bridge."
            ]
        else:
            rigor_score = 3.0
            feedback = (
                "REJECTED: AI-reported operating cash flow does not reconcile "
                "to the indirect-method identity within tolerance."
            )
            anomalies = [
                "Operating cash flow variance exceeds the declared tolerance."
            ]

        scorecard = self.build_scorecard(
            rigor_score=rigor_score,
            approved=approved,
            feedback=feedback,
            evidence={
                "currency": currency,
                "source_id": source_id,
                "fiscal_period_end": fiscal_period_end,
                "net_income": float(net_income),
                "non_cash_adjustments": float(non_cash_adjustments),
                "increase_in_net_working_capital": float(increase_in_nwc),
                "formula_operating_cash_flow": float(formula_ocf),
                "reported_ground_truth_operating_cash_flow": float(reported_ocf),
                "ai_reported_operating_cash_flow": float(ai_reported_ocf),
                "tolerance": float(tolerance),
                "ground_truth_reconciliation_delta": float(
                    ground_truth_deviation
                ),
            },
        )
        scorecard.update(
            {
                "equation_deviation_delta": float(ai_deviation),
                "working_capital_sign_inversion_detected": (
                    sign_inversion_detected
                ),
                "detected_anomalies": anomalies,
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
    result = CorporateFinancialAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
