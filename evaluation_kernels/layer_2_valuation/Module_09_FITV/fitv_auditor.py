# -*- coding: utf-8 -*-
"""Validate bond price, modified duration, and DV01 calculations."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor


class FixedIncomeAuditor(BaseAuditor):
    """Enforce one declared fixed-income pricing convention."""

    DEFAULT_RELATIVE_TOLERANCE = 0.005
    SUPPORTED_DAY_COUNT = "ACT/365F"
    SUPPORTED_FREQUENCIES = frozenset({1, 2, 4, 12})
    SUPPORTED_PRICE_BASES = frozenset({"CLEAN", "DIRTY"})
    CONSISTENT_THESES = frozenset(
        {"RATES_UP_PRICE_DOWN", "RATES_DOWN_PRICE_UP"}
    )

    @staticmethod
    def _text(payload: Mapping[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} is required and must be non-empty text.")
        return value.strip()

    @staticmethod
    def _number(
        payload: Mapping[str, Any],
        key: str,
        *,
        default: float | None = None,
        non_negative: bool = False,
        positive: bool = False,
    ) -> float:
        if key not in payload:
            if default is None:
                raise ValueError(f"{key} is required.")
            return default
        value = payload[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{key} must be numeric.")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{key} must be finite.")
        if non_negative and number < 0.0:
            raise ValueError(f"{key} must be non-negative.")
        if positive and number <= 0.0:
            raise ValueError(f"{key} must be positive.")
        return number

    @staticmethod
    def _iso_date(payload: Mapping[str, Any], key: str) -> date:
        text = FixedIncomeAuditor._text(payload, key)
        try:
            parsed = date.fromisoformat(text)
        except ValueError as error:
            raise ValueError(f"{key} must use ISO-8601 YYYY-MM-DD.") from error
        if parsed.isoformat() != text:
            raise ValueError(f"{key} must use ISO-8601 YYYY-MM-DD.")
        return parsed

    @classmethod
    def _frequency(cls, payload: Mapping[str, Any], key: str) -> int:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{key} must be an integer.")
        if value not in cls.SUPPORTED_FREQUENCIES:
            raise ValueError(
                "coupon_frequency must be one of 1, 2, 4, or 12."
            )
        return value

    @classmethod
    def _cash_flows(
        cls,
        truth: Mapping[str, Any],
        settlement_date: date,
    ) -> tuple[tuple[float, float], ...]:
        schedule = truth.get("cash_flow_schedule")
        if not isinstance(schedule, list) or not schedule:
            raise ValueError("cash_flow_schedule must be a non-empty list.")

        dated_flows: list[tuple[date, float]] = []
        for index, cash_flow in enumerate(schedule):
            if not isinstance(cash_flow, Mapping):
                raise TypeError(
                    f"cash_flow_schedule[{index}] must be an object."
                )
            payment_date = cls._iso_date(cash_flow, "payment_date")
            if payment_date <= settlement_date:
                raise ValueError(
                    "Every cash-flow payment_date must be after settlement_date."
                )
            amount = cls._number(
                cash_flow,
                "amount",
                non_negative=True,
            )
            dated_flows.append((payment_date, amount))

        payment_dates = [payment_date for payment_date, _ in dated_flows]
        if payment_dates != sorted(payment_dates):
            raise ValueError("cash_flow_schedule must be ordered by payment_date.")
        if len(payment_dates) != len(set(payment_dates)):
            raise ValueError(
                "cash_flow_schedule cannot contain duplicate payment_date values."
            )
        return tuple(
            ((payment_date - settlement_date).days / 365.0, amount)
            for payment_date, amount in dated_flows
        )

    @classmethod
    def _relative_tolerance(
        cls,
        truth: Mapping[str, Any],
        key: str,
    ) -> float:
        return cls._number(
            truth,
            key,
            default=cls.DEFAULT_RELATIVE_TOLERANCE,
            non_negative=True,
        )

    @staticmethod
    def _relative_delta(actual: float, expected: float) -> float:
        return abs(actual - expected) / max(abs(expected), 1e-12)

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        settlement_date = self._iso_date(truth, "settlement_date")
        day_count_convention = self._text(
            truth,
            "day_count_convention",
        ).upper()
        if day_count_convention != self.SUPPORTED_DAY_COUNT:
            raise ValueError(
                "day_count_convention must be ACT/365F for FITV v1."
            )
        coupon_frequency = self._frequency(truth, "coupon_frequency")
        yield_to_maturity = self._number(truth, "yield_to_maturity")
        discount_base = 1.0 + yield_to_maturity / coupon_frequency
        if discount_base <= 0.0:
            raise ValueError(
                "yield_to_maturity produces a non-positive discount base."
            )

        face_value = self._number(truth, "face_value", positive=True)
        currency = self._text(truth, "currency").upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter alphabetic code.")
        source_id = self._text(truth, "source_id")
        price_basis = self._text(truth, "price_basis").upper()
        if price_basis not in self.SUPPORTED_PRICE_BASES:
            raise ValueError("price_basis must be CLEAN or DIRTY.")
        accrued_interest = self._number(
            truth,
            "accrued_interest",
            default=0.0,
            non_negative=True,
        )
        cash_flows = self._cash_flows(truth, settlement_date)

        try:
            present_values = tuple(
                (
                    years,
                    amount
                    / math.pow(
                        discount_base,
                        coupon_frequency * years,
                    ),
                )
                for years, amount in cash_flows
            )
        except OverflowError as error:
            raise ValueError(
                "yield_to_maturity makes the discount calculation unpriceable."
            ) from error
        dirty_price = sum(value for _, value in present_values)
        if dirty_price <= 0.0:
            raise ValueError("cash_flow_schedule must produce a positive price.")
        if accrued_interest >= dirty_price:
            raise ValueError("accrued_interest must be less than dirty price.")
        clean_price = dirty_price - accrued_interest
        analytical_price = (
            clean_price if price_basis == "CLEAN" else dirty_price
        )
        macaulay_duration = (
            sum(years * value for years, value in present_values)
            / dirty_price
        )
        modified_duration = macaulay_duration / discount_base
        analytical_dv01 = modified_duration * dirty_price * 0.0001

        ai_price = self._number(ai_data, "ai_price", non_negative=True)
        ai_modified_duration = self._number(
            ai_data,
            "ai_modified_duration",
            non_negative=True,
        )
        ai_dv01 = self._number(ai_data, "ai_dv01", non_negative=True)
        trade_thesis = self._text(ai_data, "trade_thesis").upper()
        ai_price_basis = self._text(ai_data, "price_basis").upper()
        ai_day_count = self._text(
            ai_data,
            "day_count_convention",
        ).upper()
        ai_coupon_frequency = self._frequency(
            ai_data,
            "coupon_frequency",
        )

        convention_mismatches: list[str] = []
        if ai_price_basis != price_basis:
            convention_mismatches.append("price_basis")
        if ai_day_count != day_count_convention:
            convention_mismatches.append("day_count_convention")
        if ai_coupon_frequency != coupon_frequency:
            convention_mismatches.append("coupon_frequency")

        metric_deltas = {
            "price": self._relative_delta(ai_price, analytical_price),
            "modified_duration": self._relative_delta(
                ai_modified_duration,
                modified_duration,
            ),
            "dv01": self._relative_delta(ai_dv01, analytical_dv01),
        }
        tolerances = {
            "price": self._relative_tolerance(
                truth,
                "price_relative_tolerance",
            ),
            "modified_duration": self._relative_tolerance(
                truth,
                "duration_relative_tolerance",
            ),
            "dv01": self._relative_tolerance(
                truth,
                "dv01_relative_tolerance",
            ),
        }
        failed_metrics = [
            metric
            for metric, delta in metric_deltas.items()
            if delta > tolerances[metric]
        ]
        trade_thesis_consistent = trade_thesis in self.CONSISTENT_THESES
        approved = (
            not convention_mismatches
            and not failed_metrics
            and trade_thesis_consistent
        )

        if approved:
            rigor_score = 5.0
            feedback = (
                "APPROVED: price, modified duration, DV01, conventions, "
                "and rate-risk direction reconcile within tolerance."
            )
        elif convention_mismatches:
            rigor_score = 1.0
            feedback = (
                "REJECTED: AI output mixes declared fixed-income conventions: "
                + ", ".join(convention_mismatches)
                + "."
            )
        elif failed_metrics:
            rigor_score = 3.0 if len(failed_metrics) == 1 else 1.5
            feedback = (
                "REJECTED: fixed-income metric tolerance exceeded for "
                + ", ".join(failed_metrics)
                + "."
            )
        else:
            rigor_score = 2.0
            feedback = (
                "REJECTED: trade_thesis must declare "
                "RATES_UP_PRICE_DOWN or RATES_DOWN_PRICE_UP."
            )

        scorecard = self.build_scorecard(
            rigor_score=rigor_score,
            approved=approved,
            feedback=feedback,
            evidence={
                "source_id": source_id,
                "currency": currency,
                "settlement_date": settlement_date.isoformat(),
                "day_count_convention": day_count_convention,
                "coupon_frequency": coupon_frequency,
                "face_value": face_value,
                "price_basis": price_basis,
                "accrued_interest": accrued_interest,
                "dirty_price": dirty_price,
                "clean_price": clean_price,
                "macaulay_duration": macaulay_duration,
                "analytical_modified_duration": modified_duration,
                "analytical_dv01": analytical_dv01,
                "tolerances": tolerances,
            },
        )
        scorecard.update(
            {
                "analytical_price": analytical_price,
                "analytical_modified_duration": modified_duration,
                "analytical_dv01": analytical_dv01,
                "metric_deltas": metric_deltas,
                "failed_metrics": failed_metrics,
                "convention_mismatches": convention_mismatches,
                "trade_thesis_consistent": trade_thesis_consistent,
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
    result = FixedIncomeAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
