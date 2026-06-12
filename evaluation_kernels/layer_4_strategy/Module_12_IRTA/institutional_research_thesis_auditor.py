# -*- coding: utf-8 -*-
"""Audit five-year revenue theses against physical production capacity."""

from __future__ import annotations

import argparse
import json
import sys
from math import isfinite
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor


class InstitutionalResearchThesisAuditor(BaseAuditor):
    """Enforce a deterministic capacity ceiling on buy-side revenue forecasts."""

    FORECAST_YEARS = 5
    BREACH_PENALTY = 3.0

    @staticmethod
    def _positive_number(payload: Mapping[str, Any], key: str) -> float:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{key} must be numeric.")
        number = float(value)
        if not isfinite(number) or number <= 0:
            raise ValueError(f"{key} must be finite and greater than zero.")
        return number

    @classmethod
    def _numeric_series(
        cls,
        payload: Mapping[str, Any],
        key: str,
    ) -> tuple[float, ...]:
        value = payload.get(key)
        if not isinstance(value, (list, tuple)):
            raise TypeError(f"{key} must be a five-element sequence.")
        if len(value) != cls.FORECAST_YEARS:
            raise ValueError(f"{key} must contain exactly five annual values.")

        numbers: list[float] = []
        for item in value:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise TypeError(f"{key} must contain only numeric values.")
            number = float(item)
            if not isfinite(number) or number < 0:
                raise ValueError(f"{key} values must be finite and non-negative.")
            numbers.append(number)
        return tuple(numbers)

    @staticmethod
    def _forecast_cagr(revenue_forecast: tuple[float, ...]) -> float:
        if revenue_forecast[0] <= 0:
            raise ValueError("The first forecast revenue must be greater than zero.")
        periods = len(revenue_forecast) - 1
        return (revenue_forecast[-1] / revenue_forecast[0]) ** (1 / periods) - 1

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        revenue_forecast = self._numeric_series(ai_data, "revenue_forecast")
        capex_additions = self._numeric_series(truth, "capex_additions")
        current_capacity = self._positive_number(truth, "current_capacity")
        capital_efficiency = self._positive_number(truth, "capital_efficiency")
        max_utilization = self._positive_number(truth, "max_utilization")
        blended_asp = self._positive_number(truth, "blended_asp")
        if max_utilization > 1.0:
            raise ValueError("max_utilization cannot exceed 1.0.")

        capacity = current_capacity
        ceilings: list[float] = []
        implied_utilizations: list[float] = []
        breached_years: list[int] = []

        for year, (forecast, capex) in enumerate(
            zip(revenue_forecast, capex_additions),
            start=1,
        ):
            capacity += capex * capital_efficiency
            physical_revenue_capacity = capacity * blended_asp
            revenue_ceiling = physical_revenue_capacity * max_utilization
            implied_utilization = forecast / physical_revenue_capacity
            ceilings.append(revenue_ceiling)
            implied_utilizations.append(implied_utilization)
            if forecast > revenue_ceiling:
                breached_years.append(year)

        breached = bool(breached_years)
        rigor_score = 5.0 - self.BREACH_PENALTY if breached else 5.0
        if breached:
            feedback = (
                "REJECTED: the forecast exceeds the disclosed physical revenue "
                f"capacity ceiling in year(s) {breached_years}. The thesis embeds "
                "a bullish growth assumption unsupported by capacity, CapEx "
                "efficiency, utilization, and blended ASP."
            )
        else:
            feedback = (
                "APPROVED: all five forecast years remain within the deterministic "
                "capacity, utilization, and blended-ASP revenue ceiling."
            )

        scorecard = self.build_scorecard(
            rigor_score=rigor_score,
            approved=not breached,
            feedback=feedback,
            evidence={
                "revenue_ceiling_by_year": ceilings,
                "implied_utilization_by_year": implied_utilizations,
                "breached_years": breached_years,
            },
        )
        scorecard.update(
            {
                "capacity_ceiling_breached": breached,
                "implied_utilization_rate": max(implied_utilizations),
                "forecast_cagr": self._forecast_cagr(revenue_forecast),
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
    result = InstitutionalResearchThesisAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
