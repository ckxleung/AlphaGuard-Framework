# -*- coding: utf-8 -*-
"""Reconcile ledgers, trial balances, and proposed adjustments."""

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


class FinancialReconciliationAuditor(BaseAuditor):
    """Enforce cent-level reconciliation with Decimal arithmetic."""

    DEFAULT_ABSOLUTE_TOLERANCE = Decimal("0.01")

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
        non_negative: bool = True,
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
    def _currency(cls, payload: Mapping[str, Any]) -> str:
        currency = cls._text(payload, "currency").upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter alphabetic code.")
        return currency

    @classmethod
    def _iso_date_text(cls, payload: Mapping[str, Any], key: str) -> str:
        text = cls._text(payload, key)
        try:
            parsed = date.fromisoformat(text)
        except ValueError as error:
            raise ValueError(f"{key} must use ISO-8601 YYYY-MM-DD.") from error
        if parsed.isoformat() != text:
            raise ValueError(f"{key} must use ISO-8601 YYYY-MM-DD.")
        return text

    @classmethod
    def _account_mapping(cls, truth: Mapping[str, Any]) -> dict[str, str]:
        mapping = truth.get("account_mapping")
        if not isinstance(mapping, Mapping) or not mapping:
            raise ValueError("account_mapping must be a non-empty object.")
        normalized: dict[str, str] = {}
        for account, classification in mapping.items():
            if not isinstance(account, str) or not account.strip():
                raise ValueError("account_mapping keys must be non-empty text.")
            if not isinstance(classification, str) or not classification.strip():
                raise ValueError(
                    "account_mapping values must be non-empty text."
                )
            normalized[account.strip()] = classification.strip().upper()
        return normalized

    @classmethod
    def _rows(
        cls,
        truth: Mapping[str, Any],
        key: str,
        *,
        currency: str,
        period_end: str,
        account_mapping: Mapping[str, str],
        require_row_id: bool,
    ) -> tuple[dict[str, Any], ...]:
        raw_rows = truth.get(key)
        if not isinstance(raw_rows, list) or not raw_rows:
            raise ValueError(f"{key} must be a non-empty list.")

        rows: list[dict[str, Any]] = []
        seen_row_ids: set[str] = set()
        for index, raw_row in enumerate(raw_rows):
            if not isinstance(raw_row, Mapping):
                raise TypeError(f"{key}[{index}] must be an object.")
            row_currency = cls._currency(raw_row)
            if row_currency != currency:
                raise ValueError(f"{key}[{index}] currency must be {currency}.")
            row_period = cls._iso_date_text(raw_row, "period_end")
            if row_period != period_end:
                raise ValueError(
                    f"{key}[{index}] period_end must be {period_end}."
                )
            entity = cls._text(raw_row, "entity").upper()
            account = cls._text(raw_row, "account")
            if account not in account_mapping:
                raise ValueError(
                    f"{key}[{index}] account is missing from account_mapping."
                )
            debit = cls._decimal(raw_row, "debit")
            credit = cls._decimal(raw_row, "credit")
            row = {
                "entity": entity,
                "account": account,
                "debit": debit,
                "credit": credit,
                "currency": row_currency,
                "period_end": row_period,
            }
            if require_row_id:
                row_id = cls._text(raw_row, "row_id")
                if row_id in seen_row_ids:
                    raise ValueError("ledger_rows cannot contain duplicate row_id.")
                seen_row_ids.add(row_id)
                row["row_id"] = row_id
            rows.append(row)
        return tuple(rows)

    @staticmethod
    def _aggregate(rows: tuple[dict[str, Any], ...]) -> dict[str, dict[str, Decimal]]:
        aggregate: dict[str, dict[str, Decimal]] = {}
        for row in rows:
            key = f"{row['entity']}|{row['account']}"
            current = aggregate.get(
                key,
                {"debit": Decimal("0"), "credit": Decimal("0")},
            )
            aggregate[key] = {
                "debit": current["debit"] + row["debit"],
                "credit": current["credit"] + row["credit"],
            }
        return aggregate

    @classmethod
    def _ai_reconciliation(cls, ai_data: Mapping[str, Any]) -> dict[str, Any]:
        reconciliation = ai_data.get("ai_reconciliation")
        if not isinstance(reconciliation, Mapping):
            raise TypeError("ai_reconciliation must be an object.")
        is_balanced = reconciliation.get("is_balanced")
        if not isinstance(is_balanced, bool):
            raise TypeError("ai_reconciliation.is_balanced must be boolean.")
        unreconciled = reconciliation.get("unreconciled_accounts")
        if not isinstance(unreconciled, list):
            raise TypeError(
                "ai_reconciliation.unreconciled_accounts must be a list."
            )
        normalized_unreconciled = []
        for account in unreconciled:
            if not isinstance(account, str) or not account.strip():
                raise ValueError(
                    "ai_reconciliation.unreconciled_accounts must contain text."
                )
            normalized_unreconciled.append(account.strip())
        return {
            "is_balanced": is_balanced,
            "unreconciled_accounts": sorted(set(normalized_unreconciled)),
        }

    @classmethod
    def _adjustments(
        cls,
        ai_data: Mapping[str, Any],
        *,
        currency: str,
        period_end: str,
        account_mapping: Mapping[str, str],
        ledger_row_ids: frozenset[str],
        tolerance: Decimal,
    ) -> tuple[list[str], int]:
        proposed_adjustments = ai_data.get("proposed_adjustments")
        if proposed_adjustments is None:
            proposed_adjustments = []
        if not isinstance(proposed_adjustments, list):
            raise TypeError("proposed_adjustments must be a list.")

        failed_adjustments: list[str] = []
        for index, adjustment in enumerate(proposed_adjustments):
            if not isinstance(adjustment, Mapping):
                raise TypeError(f"proposed_adjustments[{index}] must be an object.")
            adjustment_id = cls._text(adjustment, "adjustment_id")
            entries = adjustment.get("entries")
            if not isinstance(entries, list) or len(entries) < 2:
                failed_adjustments.append(adjustment_id)
                continue
            debit_total = Decimal("0")
            credit_total = Decimal("0")
            traceable = True
            for entry_index, entry in enumerate(entries):
                if not isinstance(entry, Mapping):
                    raise TypeError(
                        f"proposed_adjustments[{index}].entries[{entry_index}] "
                        "must be an object."
                    )
                if cls._currency(entry) != currency:
                    raise ValueError(
                        f"proposed_adjustments[{index}] currency must be {currency}."
                    )
                if cls._iso_date_text(entry, "period_end") != period_end:
                    raise ValueError(
                        f"proposed_adjustments[{index}] period_end must be "
                        f"{period_end}."
                    )
                account = cls._text(entry, "account")
                if account not in account_mapping:
                    raise ValueError(
                        f"proposed_adjustments[{index}] account is missing from "
                        "account_mapping."
                    )
                cls._text(entry, "entity")
                debit_total += cls._decimal(entry, "debit")
                credit_total += cls._decimal(entry, "credit")
                source_row_ids = entry.get("source_row_ids")
                if not isinstance(source_row_ids, list) or not source_row_ids:
                    traceable = False
                    continue
                for row_id in source_row_ids:
                    if not isinstance(row_id, str) or row_id not in ledger_row_ids:
                        traceable = False
            if abs(debit_total - credit_total) > tolerance or not traceable:
                failed_adjustments.append(adjustment_id)
        return failed_adjustments, len(proposed_adjustments)

    def execute_audit(self, ai_output: dict, ground_truth: dict) -> dict:
        ai_data, truth = self.validate_inputs(ai_output, ground_truth)
        currency = self._currency(truth)
        period_end = self._iso_date_text(truth, "period_end")
        source_id = self._text(truth, "source_id")
        tolerance = self._decimal(
            truth,
            "absolute_tolerance",
            default=self.DEFAULT_ABSOLUTE_TOLERANCE,
        )
        account_mapping = self._account_mapping(truth)
        ledger_rows = self._rows(
            truth,
            "ledger_rows",
            currency=currency,
            period_end=period_end,
            account_mapping=account_mapping,
            require_row_id=True,
        )
        trial_balance_rows = self._rows(
            truth,
            "trial_balance",
            currency=currency,
            period_end=period_end,
            account_mapping=account_mapping,
            require_row_id=False,
        )
        ledger_row_ids = frozenset(str(row["row_id"]) for row in ledger_rows)
        ledger_totals = self._aggregate(ledger_rows)
        trial_balance_totals = self._aggregate(trial_balance_rows)
        ledger_debits = sum(row["debit"] for row in ledger_rows)
        ledger_credits = sum(row["credit"] for row in ledger_rows)
        ledger_balance_delta = abs(ledger_debits - ledger_credits)

        all_keys = sorted(set(ledger_totals) | set(trial_balance_totals))
        account_variances: dict[str, float] = {}
        unreconciled_accounts: list[str] = []
        variance_delta = Decimal("0")
        for key in all_keys:
            ledger_total = ledger_totals.get(
                key,
                {"debit": Decimal("0"), "credit": Decimal("0")},
            )
            trial_balance_total = trial_balance_totals.get(
                key,
                {"debit": Decimal("0"), "credit": Decimal("0")},
            )
            net_variance = (
                ledger_total["debit"]
                - ledger_total["credit"]
                - trial_balance_total["debit"]
                + trial_balance_total["credit"]
            )
            absolute_variance = abs(net_variance)
            if absolute_variance > tolerance:
                unreconciled_accounts.append(key)
                account_variances[key] = float(absolute_variance)
            variance_delta += absolute_variance

        failed_adjustments, adjustment_count = self._adjustments(
            ai_data,
            currency=currency,
            period_end=period_end,
            account_mapping=account_mapping,
            ledger_row_ids=ledger_row_ids,
            tolerance=tolerance,
        )
        ai_reconciliation = self._ai_reconciliation(ai_data)
        analytical_balanced = (
            ledger_balance_delta <= tolerance and not unreconciled_accounts
        )
        ai_claim_consistent = (
            ai_reconciliation["is_balanced"] == analytical_balanced
            and ai_reconciliation["unreconciled_accounts"]
            == sorted(unreconciled_accounts)
        )
        adjustments_traceable = not failed_adjustments
        approved = analytical_balanced and adjustments_traceable and ai_claim_consistent

        if approved:
            rigor_score = 5.0
            feedback = (
                "APPROVED: ledger totals, trial balance, and proposed "
                "adjustments reconcile within cent-level tolerance."
            )
        elif not analytical_balanced:
            rigor_score = 2.0
            feedback = (
                "REJECTED: ledger or trial-balance variance exceeds the "
                "declared monetary tolerance."
            )
        elif not adjustments_traceable:
            rigor_score = 1.5
            feedback = (
                "REJECTED: at least one proposed adjustment is unbalanced or "
                "lacks source-row traceability."
            )
        else:
            rigor_score = 2.5
            feedback = (
                "REJECTED: AI reconciliation claim does not match the "
                "deterministic ledger evidence."
            )

        scorecard = self.build_scorecard(
            rigor_score=rigor_score,
            approved=approved,
            feedback=feedback,
            evidence={
                "source_id": source_id,
                "currency": currency,
                "period_end": period_end,
                "absolute_tolerance": float(tolerance),
                "ledger_row_count": len(ledger_rows),
                "trial_balance_row_count": len(trial_balance_rows),
                "proposed_adjustment_count": adjustment_count,
                "ledger_debits": float(ledger_debits),
                "ledger_credits": float(ledger_credits),
                "ledger_balance_delta": float(ledger_balance_delta),
                "account_variances": account_variances,
            },
        )
        scorecard.update(
            {
                "is_balanced": analytical_balanced,
                "variance_delta": float(variance_delta),
                "unreconciled_accounts": unreconciled_accounts,
                "adjustment_traceability_status": (
                    "TRACEABLE" if adjustments_traceable else "FAILED"
                ),
                "failed_adjustments": failed_adjustments,
                "ai_reconciliation_claim_consistent": ai_claim_consistent,
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
    result = FinancialReconciliationAuditor().execute_audit(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
