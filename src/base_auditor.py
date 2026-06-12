# -*- coding: utf-8 -*-
"""Shared execution contract for every AlphaGuard evaluation kernel."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from math import isfinite
from typing import Any, Dict, Mapping


class BaseAuditor(ABC):
    """Uniform interface implemented by all AlphaGuard auditors."""

    REQUIRED_SCORECARD_KEYS = frozenset(
        {
            "rigor_score",
            "data_quality_status",
            "structured_written_feedback",
        }
    )
    VALID_DATA_QUALITY_STATUSES = frozenset({"APPROVED", "REJECTED"})

    @abstractmethod
    def execute_audit(self, ai_output: Dict, ground_truth: Dict) -> Dict:
        """Audit an AI artifact against deterministic ground truth."""

    @classmethod
    def validate_inputs(
        cls,
        ai_output: Mapping[str, Any],
        ground_truth: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Validate and copy boundary inputs so kernels never mutate callers."""
        if not isinstance(ai_output, Mapping):
            raise TypeError("ai_output must be a mapping.")
        if not isinstance(ground_truth, Mapping):
            raise TypeError("ground_truth must be a mapping.")
        return dict(ai_output), dict(ground_truth)

    @classmethod
    def validate_scorecard(cls, scorecard: Mapping[str, Any]) -> dict[str, Any]:
        """Enforce the institutional scorecard contract."""
        if not isinstance(scorecard, Mapping):
            raise TypeError("scorecard must be a mapping.")

        missing = cls.REQUIRED_SCORECARD_KEYS.difference(scorecard)
        if missing:
            raise ValueError(
                "scorecard is missing required keys: " + ", ".join(sorted(missing))
            )

        rigor_score = scorecard["rigor_score"]
        if isinstance(rigor_score, bool) or not isinstance(rigor_score, (int, float)):
            raise TypeError("rigor_score must be numeric.")
        rigor_score = float(rigor_score)
        if not isfinite(rigor_score) or not 0.0 <= rigor_score <= 5.0:
            raise ValueError("rigor_score must be finite and between 0.0 and 5.0.")

        status = scorecard["data_quality_status"]
        if status not in cls.VALID_DATA_QUALITY_STATUSES:
            raise ValueError(
                "data_quality_status must be APPROVED or REJECTED."
            )

        feedback = scorecard["structured_written_feedback"]
        if not isinstance(feedback, str) or not feedback.strip():
            raise ValueError("structured_written_feedback must be non-empty text.")

        validated = dict(scorecard)
        validated.update(
            {
                "rigor_score": rigor_score,
                "data_quality_status": status,
                "structured_written_feedback": feedback.strip(),
            }
        )
        return validated

    @classmethod
    def build_scorecard(
        cls,
        *,
        rigor_score: float,
        approved: bool,
        feedback: str,
        evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build and validate a standard scorecard without mutating evidence."""
        scorecard: dict[str, Any] = {
            "rigor_score": rigor_score,
            "data_quality_status": "APPROVED" if approved else "REJECTED",
            "structured_written_feedback": feedback,
        }
        if evidence is not None:
            scorecard["evidence"] = dict(evidence)
        return cls.validate_scorecard(scorecard)


def main() -> int:  # pragma: no cover
    """Run a lightweight contract self-check."""
    sample = BaseAuditor.build_scorecard(
        rigor_score=5.0,
        approved=True,
        feedback="Base scorecard contract is valid.",
    )
    print(json.dumps(sample, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
