# -*- coding: utf-8 -*-
"""Validate DCF bridges, per-share valuation, and comparable multiples."""

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


class CoreValuationAuditor(BaseAuditor):
    """Enforce deterministic DCF and comparable-company valuation math."""

    DEFAULT_VALUATION_TOLERANCE = 0.02
    DEFAULT_MULTIPLE_TOLERANCE = 0.02
    SUPPORTED_TERMINAL_METHODS = frozenset({"GORDON_GROWTH"})
    SUPPORTED_NUMERATOR_BASES = frozenset(
        {"ENTERPRISE_VALUE", "EQUITY_VALUE"}
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

    @classmethod
    def _currency(cls, payload: Mapping[str, Any]) -> str:
        currency = cls._text(payload, "currency").upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter alphabetic code.")
        return currency

    @classmethod
    def _iso_date(cls, payload: Mapping[str, Any], key: str) -> date:
        text = cls._text(payload, key)
        try:
            parsed = date.fromisoformat(text)
        except ValueError as error:
            raise ValueError(f"{key} must use ISO-8601 YYYY-MM-DD.") from error
        if parsed.isoformat() != text:
            raise ValueError(f"{key} must use ISO-8601 YYYY-MM-DD.")
        return parsed

    @classmethod
    def _cash_flows(cls, truth: Mapping[str, Any]) -> tuple[float, ...]:
        raw_cash_flows = truth.get("forecast_free_cash_flows")
        if not isinstance(raw_cash_flows, list) or not raw_cash_flows:
            raise ValueError(
                "forecast_free_cash_flows must be a non-empty list."
            )
        cash_flows: list[float] = []
        for index, value in enumerate(raw_cash_flows):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"forecast_free_cash_flows[{index}] must be numeric."
                )
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(
                    f"forecast_free_cash_flows[{index}] must be finite."
                )
            cash_flows.append(number)
        return tuple(cash_flows)

    @staticmethod
    def _relative_delta(actual: float, expected: float) -> float:
        return abs(actual - expected) / max(abs(expected), 1e-12)

    @classmethod
    def _relative_tolerance(
        cls,
        truth: Mapping[str, Any],
        key: str,
        default: float,
    ) -> float:
        return cls._number(truth, key, default=default, non_negative=True)

    @classmethod
    def _comparable_metrics(
        cls,
        truth: Mapping[str, Any],
    ) -> dict[str, dict[str, Any]]:
        raw_metrics = truth.get("comparable_company_metrics")
        if not isinstance(raw_metrics, list) or not raw_metrics:
            raise ValueError(
                "comparable_company_metrics must be a non-empty list."
            )

        metrics: dict[str, dict[str, Any]] = {}
        for index, metric in enumerate(raw_metrics):
            if not isinstance(metric, Mapping):
                raise TypeError(
                    f"comparable_company_metrics[{index}] must be an object."
                )
            metric_name = cls._text(metric, "metric_name").upper()
            if metric_name in metrics:
                raise ValueError(
                    f"comparable_company_metrics contains duplicate {metric_name}."
                )
            numerator_basis = cls._text(metric, "numerator_basis").upper()
            if numerator_basis not in cls.SUPPORTED_NUMERATOR_BASES:
                raise ValueError(
                    "numerator_basis must be ENTERPRISE_VALUE or EQUITY_VALUE."
                )
            denominator_period = cls._text(metric, "denominator_period").upper()
            numerator = cls._number(metric, "numerator")
            denominator = cls._number(metric, "denominator", positive=True)
            metrics[metric_name] = {
                "metric_name": metric_name,
                "numerator_basis": numerator_basis,
                "numerator": numerator,
                "denominator": denominator,
                "denominator_period": denominator_period,
                "analytical_multiple": numerator / denominator,
            }
        return metrics

    @classmethod
    def _ai_multiples(cls, ai_data: Mapping[str, Any]) -> dict[str, float]:
        raw_multiples = ai_data.get("ai_multiples")
        if not isinstance(raw_multiples, Mapping):
            raise TypeError("ai_multiples must be an object.")
        multiples: dict[str, float] = {}
        for raw_name, raw_value in raw_multiples.items():
            if not isinstance(raw_name, str) or not raw_name.strip():
                raise ValueError("ai_multiples keys must be non-empty text.")
            if isinstance(raw_value, bool) or not isinstance(
                raw_value,
                (int, float),
            ):
                raise TypeError(f"ai_multiples.{raw_name} must be numeric.")
            value = float(raw_value)
            if not math.isfinite(value):
                raise ValueError(f"ai_multiples.{raw_name} must be finite.")
            multiples[raw_name.strip().upper()] = value
        return multiples

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        cash_flows = self._cash_flows(truth)
        wacc = self._number(truth, "wacc")
        terminal_growth_rate = self._number(truth, "terminal_growth_rate")
        if wacc <= terminal_growth_rate:
            raise ValueError("WACC must exceed terminal_growth_rate.")
        if 1.0 + wacc <= 0.0:
            raise ValueError("wacc produces a non-positive discount base.")

        net_debt = self._number(truth, "net_debt")
        diluted_shares = self._number(truth, "diluted_shares", positive=True)
        currency = self._currency(truth)
        valuation_date = self._iso_date(truth, "valuation_date")
        share_count_basis = self._text(truth, "share_count_basis").upper()
        source_id = self._text(truth, "source_id")
        valuation_tolerance = self._relative_tolerance(
            truth,
            "valuation_relative_tolerance",
            self.DEFAULT_VALUATION_TOLERANCE,
        )
        multiple_tolerance = self._relative_tolerance(
            truth,
            "multiple_relative_tolerance",
            self.DEFAULT_MULTIPLE_TOLERANCE,
        )

        present_value_cash_flows = sum(
            cash_flow / math.pow(1.0 + wacc, year)
            for year, cash_flow in enumerate(cash_flows, start=1)
        )
        terminal_value = cash_flows[-1] * (1.0 + terminal_growth_rate) / (
            wacc - terminal_growth_rate
        )
        discounted_terminal_value = terminal_value / math.pow(
            1.0 + wacc,
            len(cash_flows),
        )
        enterprise_value = present_value_cash_flows + discounted_terminal_value
        equity_value = enterprise_value - net_debt
        price_per_share = equity_value / diluted_shares

        ai_enterprise_value = self._number(
            ai_data,
            "ai_enterprise_value",
        )
        ai_equity_value = self._number(ai_data, "ai_equity_value")
        ai_price_per_share = self._number(ai_data, "ai_price_per_share")
        ai_currency = self._currency(ai_data)
        ai_valuation_date = self._iso_date(ai_data, "valuation_date")
        ai_share_count_basis = self._text(ai_data, "share_count_basis").upper()
        terminal_value_method = self._text(
            ai_data,
            "terminal_value_method",
        ).upper()

        convention_mismatches: list[str] = []
        if ai_currency != currency:
            convention_mismatches.append("currency")
        if ai_valuation_date != valuation_date:
            convention_mismatches.append("valuation_date")
        if ai_share_count_basis != share_count_basis:
            convention_mismatches.append("share_count_basis")
        if terminal_value_method not in self.SUPPORTED_TERMINAL_METHODS:
            convention_mismatches.append("terminal_value_method")

        valuation_deltas = {
            "enterprise_value": self._relative_delta(
                ai_enterprise_value,
                enterprise_value,
            ),
            "equity_value": self._relative_delta(ai_equity_value, equity_value),
            "price_per_share": self._relative_delta(
                ai_price_per_share,
                price_per_share,
            ),
        }
        failed_metrics = [
            metric
            for metric, delta in valuation_deltas.items()
            if delta > valuation_tolerance
        ]

        comparable_metrics = self._comparable_metrics(truth)
        ai_multiples = self._ai_multiples(ai_data)
        calculated_multiples = {
            name: metric["analytical_multiple"]
            for name, metric in comparable_metrics.items()
        }
        missing_multiples = [
            name for name in comparable_metrics if name not in ai_multiples
        ]
        multiple_deltas = {
            name: self._relative_delta(ai_multiples[name], expected)
            for name, expected in calculated_multiples.items()
            if name in ai_multiples
        }
        failed_multiples = [
            name
            for name, delta in multiple_deltas.items()
            if delta > multiple_tolerance
        ]

        approved = (
            not convention_mismatches
            and not failed_metrics
            and not failed_multiples
            and not missing_multiples
        )
        if approved:
            rigor_score = 5.0
            feedback = (
                "APPROVED: DCF bridge, per-share valuation, declared "
                "conventions, and comparable multiples reconcile within tolerance."
            )
        elif convention_mismatches:
            rigor_score = 1.0
            feedback = (
                "REJECTED: AI output mixes valuation conventions: "
                + ", ".join(convention_mismatches)
                + "."
            )
        elif failed_metrics:
            rigor_score = 3.0 if len(failed_metrics) == 1 else 1.5
            feedback = (
                "REJECTED: DCF valuation tolerance exceeded for "
                + ", ".join(failed_metrics)
                + "."
            )
        else:
            rigor_score = 2.0
            multiple_issues = failed_multiples + missing_multiples
            feedback = (
                "REJECTED: comparable-company multiple tolerance failed for "
                + ", ".join(multiple_issues)
                + "."
            )

        scorecard = self.build_scorecard(
            rigor_score=rigor_score,
            approved=approved,
            feedback=feedback,
            evidence={
                "source_id": source_id,
                "currency": currency,
                "valuation_date": valuation_date.isoformat(),
                "share_count_basis": share_count_basis,
                "wacc": wacc,
                "terminal_growth_rate": terminal_growth_rate,
                "net_debt": net_debt,
                "diluted_shares": diluted_shares,
                "present_value_cash_flows": present_value_cash_flows,
                "terminal_value": terminal_value,
                "discounted_terminal_value": discounted_terminal_value,
                "valuation_relative_tolerance": valuation_tolerance,
                "multiple_relative_tolerance": multiple_tolerance,
            },
        )
        scorecard.update(
            {
                "ground_truth_enterprise_value": enterprise_value,
                "ground_truth_equity_value": equity_value,
                "ground_truth_price_per_share": price_per_share,
                "valuation_deltas": valuation_deltas,
                "failed_metrics": failed_metrics,
                "calculated_multiples": calculated_multiples,
                "multiple_deltas": multiple_deltas,
                "failed_multiples": failed_multiples,
                "missing_multiples": missing_multiples,
                "convention_mismatches": convention_mismatches,
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
    result = CoreValuationAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
