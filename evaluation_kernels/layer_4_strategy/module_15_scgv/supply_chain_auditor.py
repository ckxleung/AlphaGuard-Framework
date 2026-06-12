# -*- coding: utf-8 -*-
"""Validate stochastic safety stock and reorder-point calculations."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor


class SupplyChainAuditor(BaseAuditor):
    """Enforce the dual-variance industrial engineering ROP equation."""

    SERVICE_LEVEL_Z = {
        0.90: 1.28,
        0.95: 1.65,
        0.99: 2.33,
        0.999: 3.09,
    }
    RELATIVE_TOLERANCE = 0.01
    ABSOLUTE_TOLERANCE = 0.01

    @staticmethod
    def _number(
        payload: Mapping[str, Any],
        key: str,
        *,
        allow_zero: bool = False,
    ) -> float:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{key} must be numeric.")
        number = float(value)
        minimum_valid = number >= 0 if allow_zero else number > 0
        if not math.isfinite(number) or not minimum_valid:
            qualifier = "non-negative" if allow_zero else "greater than zero"
            raise ValueError(f"{key} must be finite and {qualifier}.")
        return number

    @classmethod
    def _resolve_z_score(cls, truth: Mapping[str, Any]) -> tuple[float, float]:
        service_level = cls._number(truth, "service_level")
        if service_level >= 1.0:
            raise ValueError("service_level must be below 1.0.")
        if "z_score" in truth:
            return cls._number(truth, "z_score"), service_level

        for known_level, z_score in cls.SERVICE_LEVEL_Z.items():
            if math.isclose(service_level, known_level, abs_tol=1e-9):
                return z_score, service_level
        raise ValueError(
            "Unsupported service_level; provide an explicit positive z_score."
        )

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        average_demand = self._number(truth, "average_demand")
        average_lead_time = self._number(truth, "average_lead_time")
        demand_std = self._number(truth, "demand_std", allow_zero=True)
        lead_time_std = self._number(truth, "lead_time_std", allow_zero=True)
        z_score, service_level = self._resolve_z_score(truth)
        ai_reorder_point = self._number(ai_data, "reorder_point", allow_zero=True)
        ai_safety_stock = self._number(ai_data, "safety_stock", allow_zero=True)

        variance = (
            average_lead_time * demand_std**2
            + average_demand**2 * lead_time_std**2
        )
        expected_safety_stock = z_score * math.sqrt(variance)
        expected_reorder_point = (
            average_demand * average_lead_time + expected_safety_stock
        )
        deviation = abs(ai_reorder_point - expected_reorder_point)
        safety_stock_deviation = abs(ai_safety_stock - expected_safety_stock)
        tolerance = max(
            self.ABSOLUTE_TOLERANCE,
            expected_reorder_point * self.RELATIVE_TOLERANCE,
        )
        safety_tolerance = max(
            self.ABSOLUTE_TOLERANCE,
            expected_safety_stock * self.RELATIVE_TOLERANCE,
        )

        linear_safety_stock = z_score * (demand_std + lead_time_std)
        linear_reorder_point = (
            average_demand * average_lead_time + linear_safety_stock
        )
        linear_shortcut_detected = (
            math.isclose(
                ai_reorder_point,
                linear_reorder_point,
                abs_tol=max(self.ABSOLUTE_TOLERANCE, abs(linear_reorder_point) * 0.001),
            )
            or "linear" in str(ai_data.get("methodology", "")).lower()
        )
        approved = (
            deviation <= tolerance
            and safety_stock_deviation <= safety_tolerance
            and not linear_shortcut_detected
        )

        relative_error = deviation / max(expected_reorder_point, 1.0)
        rigor_score = 5.0 if approved else max(0.0, 5.0 - min(4.0, relative_error * 20.0))
        if linear_shortcut_detected:
            rigor_score = min(rigor_score, 2.0)

        if approved:
            feedback = (
                "APPROVED: safety stock and reorder point reconcile to the "
                "dual-variance stochastic equation within the 1% tolerance."
            )
        else:
            feedback = (
                "REJECTED: the proposed inventory policy does not reconcile to "
                "the demand and lead-time variance equation, or it uses a linear "
                "uncertainty shortcut that understates stockout risk."
            )

        scorecard = self.build_scorecard(
            rigor_score=rigor_score,
            approved=approved,
            feedback=feedback,
            evidence={
                "expected_safety_stock": expected_safety_stock,
                "expected_reorder_point": expected_reorder_point,
                "z_score": z_score,
                "tolerance": tolerance,
                "safety_stock_deviation": safety_stock_deviation,
            },
        )
        scorecard.update(
            {
                "inventory_stockout_risk_pct": (1.0 - service_level) * 100.0,
                "equation_deviation_delta": deviation,
                "linear_shortcut_detected": linear_shortcut_detected,
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
    result = SupplyChainAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
