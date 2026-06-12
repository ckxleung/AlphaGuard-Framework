# -*- coding: utf-8 -*-
"""Separate institutional flow from retail sentiment noise."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor


class BehavioralMarketAuditor(BaseAuditor):
    """Audit sentiment recommendations against market-microstructure evidence."""

    DISCUSSION_SPIKE_THRESHOLD = 2.0
    STRONG_BUY_LABELS = frozenset({"STRONG BUY", "STRONG_BUY", "STRONGBUY"})
    EPSILON = 1e-12

    @staticmethod
    def _series(payload: Mapping[str, Any], key: str) -> tuple[float, ...]:
        value = payload.get(key)
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            raise ValueError(f"{key} must contain at least three numeric values.")
        numbers: list[float] = []
        for item in value:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise TypeError(f"{key} must contain only numeric values.")
            number = float(item)
            if not math.isfinite(number):
                raise ValueError(f"{key} must contain finite values.")
            numbers.append(number)
        return tuple(numbers)

    @staticmethod
    def _covariance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        if len(left) != len(right):
            raise ValueError("Microstructure series must have equal lengths.")
        left_mean = statistics.fmean(left)
        right_mean = statistics.fmean(right)
        return statistics.fmean(
            (x - left_mean) * (y - right_mean)
            for x, y in zip(left, right)
        )

    @classmethod
    def _signal_to_noise_db(
        cls,
        sentiment: tuple[float, ...],
        price_changes: tuple[float, ...],
    ) -> float:
        if len(sentiment) != len(price_changes):
            raise ValueError("sentiment_changes and price_changes must align.")
        signal_power = statistics.fmean(value * value for value in price_changes)
        residual_power = statistics.fmean(
            (sentiment_value - price_value) ** 2
            for sentiment_value, price_value in zip(sentiment, price_changes)
        )
        return 10.0 * math.log10(
            (signal_power + cls.EPSILON) / (residual_power + cls.EPSILON)
        )

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        sentiment = self._series(ai_data, "sentiment_changes")
        block_outflow = self._series(truth, "block_trades_outflow")
        retail_imbalance = self._series(truth, "retail_orderflow_imbalance")
        discussion_volume = self._series(truth, "discussion_volume")
        price_changes = self._series(truth, "price_changes")

        lengths = {
            len(sentiment),
            len(block_outflow),
            len(retail_imbalance),
            len(discussion_volume),
            len(price_changes),
        }
        if len(lengths) != 1:
            raise ValueError("All behavioral and microstructure series must align.")
        if any(abs(value) <= self.EPSILON for value in retail_imbalance):
            raise ValueError("retail_orderflow_imbalance cannot contain zero.")

        flow_ratio = tuple(
            outflow / imbalance
            for outflow, imbalance in zip(block_outflow, retail_imbalance)
        )
        purity = self._covariance(sentiment, flow_ratio)
        prior_discussion = statistics.median(discussion_volume[:-1])
        if prior_discussion <= 0:
            raise ValueError("Historical discussion volume must be positive.")
        noise_inflation_ratio = discussion_volume[-1] / prior_discussion
        signal_to_noise_db = self._signal_to_noise_db(sentiment, price_changes)

        rating = str(ai_data.get("rating", "")).strip().upper()
        discussion_spike = noise_inflation_ratio >= self.DISCUSSION_SPIKE_THRESHOLD
        institutional_outflow = block_outflow[-1] > 0
        price_divergence = price_changes[-1] <= 0
        strong_buy = rating in self.STRONG_BUY_LABELS
        failed = (
            discussion_spike
            and institutional_outflow
            and price_divergence
            and strong_buy
        )

        rigor_score = 1.0 if failed else 5.0
        if failed:
            feedback = (
                "REJECTED: a retail discussion spike coincides with institutional "
                "block-trade outflow and non-positive price confirmation, yet the "
                "AI artifact issues a Strong Buy rating. The noise filter failed."
            )
        else:
            feedback = (
                "APPROVED: the recommendation does not violate the deterministic "
                "discussion-volume, block-flow, and price-divergence rejection rule."
            )

        scorecard = self.build_scorecard(
            rigor_score=rigor_score,
            approved=not failed,
            feedback=feedback,
            evidence={
                "discussion_spike": discussion_spike,
                "institutional_outflow": institutional_outflow,
                "price_divergence": price_divergence,
                "rating": rating,
            },
        )
        scorecard.update(
            {
                "noise_inflation_ratio": noise_inflation_ratio,
                "signal_to_noise_db": signal_to_noise_db,
                "signal_purity_coefficient": purity,
                "noise_filter_failed": failed,
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
    result = BehavioralMarketAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
