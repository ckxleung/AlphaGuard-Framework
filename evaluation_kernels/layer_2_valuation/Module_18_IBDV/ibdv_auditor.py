# -*- coding: utf-8 -*-
"""Audit investment-banking enterprise-value capital bridges."""

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


class InvestmentBankingDealAuditor(BaseAuditor):
    """Enforce a deterministic equity-value-to-enterprise-value bridge."""

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

    @staticmethod
    def _omitted_components(
        ai_enterprise_value: Decimal,
        base_enterprise_value: Decimal,
        preferred_stock: Decimal,
        non_controlling_interests: Decimal,
        tolerance: Decimal,
    ) -> list[str]:
        if (
            preferred_stock > tolerance
            and non_controlling_interests > tolerance
            and abs(ai_enterprise_value - base_enterprise_value) <= tolerance
        ):
            return ["preferred_stock", "non_controlling_interests"]

        full_enterprise_value = (
            base_enterprise_value
            + preferred_stock
            + non_controlling_interests
        )
        if (
            non_controlling_interests > tolerance
            and abs(
                ai_enterprise_value
                - (full_enterprise_value - non_controlling_interests)
            )
            <= tolerance
        ):
            return ["non_controlling_interests"]
        if (
            preferred_stock > tolerance
            and abs(ai_enterprise_value - (full_enterprise_value - preferred_stock))
            <= tolerance
        ):
            return ["preferred_stock"]
        return []

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        equity_value = self._decimal(
            truth,
            "equity_value",
            non_negative=True,
        )
        total_debt = self._decimal(
            truth,
            "total_debt",
            non_negative=True,
        )
        cash_and_equivalents = self._decimal(
            truth,
            "cash_and_equivalents",
            non_negative=True,
        )
        preferred_stock = self._decimal(
            truth,
            "preferred_stock",
            non_negative=True,
        )
        non_controlling_interests = self._decimal(
            truth,
            "non_controlling_interests",
            non_negative=True,
        )
        reported_enterprise_value = self._decimal(
            truth,
            "reported_enterprise_value",
        )
        ai_enterprise_value = self._decimal(
            ai_data,
            "calculated_enterprise_value",
        )

        currency = self._text(truth, "currency").upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter alphabetic code.")
        equity_value_basis = self._text(truth, "equity_value_basis")
        source_id = self._text(truth, "source_id")
        valuation_date = self._text(truth, "valuation_date")
        try:
            parsed_valuation_date = date.fromisoformat(valuation_date)
        except ValueError as error:
            raise ValueError(
                "valuation_date must use ISO-8601 YYYY-MM-DD format."
            ) from error
        if parsed_valuation_date.isoformat() != valuation_date:
            raise ValueError(
                "valuation_date must use ISO-8601 YYYY-MM-DD format."
            )

        base_enterprise_value = equity_value + total_debt - cash_and_equivalents
        formula_enterprise_value = (
            base_enterprise_value
            + preferred_stock
            + non_controlling_interests
        )
        tolerance = self._tolerance(truth, formula_enterprise_value)
        ground_truth_deviation = abs(
            reported_enterprise_value - formula_enterprise_value
        )
        if ground_truth_deviation > tolerance:
            raise ValueError(
                "reported ground truth enterprise value does not reconcile to "
                "equity value + debt - cash + preferred stock + "
                "non-controlling interests within tolerance."
            )

        ai_deviation = abs(ai_enterprise_value - formula_enterprise_value)
        omitted_components = self._omitted_components(
            ai_enterprise_value,
            base_enterprise_value,
            preferred_stock,
            non_controlling_interests,
            tolerance,
        )
        omission_detected = bool(omitted_components)
        approved = ai_deviation <= tolerance and not omission_detected

        if approved:
            rigor_score = 5.0
            feedback = (
                "APPROVED: AI-calculated enterprise value reconciles to the "
                "declared capital bridge within tolerance."
            )
            anomalies: list[str] = []
        elif omission_detected:
            rigor_score = 1.0 if len(omitted_components) == 2 else 1.5
            feedback = (
                "REJECTED: capital-bridge omission detected for "
                + ", ".join(omitted_components)
                + "."
            )
            anomalies = [
                "Enterprise-value bridge omitted: "
                + ", ".join(omitted_components)
                + "."
            ]
        else:
            rigor_score = 3.0
            feedback = (
                "REJECTED: AI-calculated enterprise value does not reconcile "
                "to the declared capital bridge within tolerance."
            )
            anomalies = [
                "Enterprise-value variance exceeds the declared tolerance."
            ]

        scorecard = self.build_scorecard(
            rigor_score=rigor_score,
            approved=approved,
            feedback=feedback,
            evidence={
                "currency": currency,
                "equity_value_basis": equity_value_basis,
                "source_id": source_id,
                "valuation_date": valuation_date,
                "equity_value": float(equity_value),
                "total_debt": float(total_debt),
                "cash_and_equivalents": float(cash_and_equivalents),
                "preferred_stock": float(preferred_stock),
                "non_controlling_interests": float(
                    non_controlling_interests
                ),
                "formula_enterprise_value": float(formula_enterprise_value),
                "reported_ground_truth_enterprise_value": float(
                    reported_enterprise_value
                ),
                "ai_calculated_enterprise_value": float(ai_enterprise_value),
                "tolerance": float(tolerance),
                "ground_truth_reconciliation_delta": float(
                    ground_truth_deviation
                ),
            },
        )
        scorecard.update(
            {
                "equation_deviation_delta": float(ai_deviation),
                "capital_bridge_omission_detected": omission_detected,
                "omitted_bridge_components": omitted_components,
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
    result = InvestmentBankingDealAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
