from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FinancialReconciliationAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        from evaluation_kernels.layer_3_compliance.Module_08_FOAS.foas_auditor import (
            FinancialReconciliationAuditor,
        )

        self.auditor = FinancialReconciliationAuditor()
        self.ground_truth = {
            "ledger_rows": [
                {
                    "row_id": "L1",
                    "entity": "ALPHA_US",
                    "account": "1000_CASH",
                    "debit": "1000.00",
                    "credit": "0.00",
                    "currency": "USD",
                    "period_end": "2026-03-31",
                },
                {
                    "row_id": "L2",
                    "entity": "ALPHA_US",
                    "account": "4000_REVENUE",
                    "debit": "0.00",
                    "credit": "1000.00",
                    "currency": "USD",
                    "period_end": "2026-03-31",
                },
                {
                    "row_id": "L3",
                    "entity": "ALPHA_US",
                    "account": "6100_EXPENSE",
                    "debit": "250.00",
                    "credit": "0.00",
                    "currency": "USD",
                    "period_end": "2026-03-31",
                },
                {
                    "row_id": "L4",
                    "entity": "ALPHA_US",
                    "account": "2000_PAYABLES",
                    "debit": "0.00",
                    "credit": "250.00",
                    "currency": "USD",
                    "period_end": "2026-03-31",
                },
            ],
            "trial_balance": [
                {
                    "entity": "ALPHA_US",
                    "account": "1000_CASH",
                    "debit": "1000.00",
                    "credit": "0.00",
                    "currency": "USD",
                    "period_end": "2026-03-31",
                },
                {
                    "entity": "ALPHA_US",
                    "account": "4000_REVENUE",
                    "debit": "0.00",
                    "credit": "1000.00",
                    "currency": "USD",
                    "period_end": "2026-03-31",
                },
                {
                    "entity": "ALPHA_US",
                    "account": "6100_EXPENSE",
                    "debit": "250.00",
                    "credit": "0.00",
                    "currency": "USD",
                    "period_end": "2026-03-31",
                },
                {
                    "entity": "ALPHA_US",
                    "account": "2000_PAYABLES",
                    "debit": "0.00",
                    "credit": "250.00",
                    "currency": "USD",
                    "period_end": "2026-03-31",
                },
            ],
            "account_mapping": {
                "1000_CASH": "ASSET",
                "4000_REVENUE": "REVENUE",
                "6100_EXPENSE": "EXPENSE",
                "2000_PAYABLES": "LIABILITY",
            },
            "currency": "USD",
            "period_end": "2026-03-31",
            "source_id": "DOC-SYNTHETIC-ALPHAGUARD-001",
            "absolute_tolerance": "0.01",
        }

    def valid_ai_output(self) -> dict:
        return {
            "ai_reconciliation": {
                "is_balanced": True,
                "total_debits": "1250.00",
                "total_credits": "1250.00",
                "unreconciled_accounts": [],
            },
            "proposed_adjustments": [
                {
                    "adjustment_id": "ADJ-001",
                    "entries": [
                        {
                            "entity": "ALPHA_US",
                            "account": "6100_EXPENSE",
                            "debit": "10.00",
                            "credit": "0.00",
                            "currency": "USD",
                            "period_end": "2026-03-31",
                            "source_row_ids": ["L3"],
                        },
                        {
                            "entity": "ALPHA_US",
                            "account": "2000_PAYABLES",
                            "debit": "0.00",
                            "credit": "10.00",
                            "currency": "USD",
                            "period_end": "2026-03-31",
                            "source_row_ids": ["L4"],
                        },
                    ],
                }
            ],
            "control_narrative": (
                "Ledger rows reconcile to the trial balance; proposed "
                "adjustments are balanced and source-row traced."
            ),
        }

    def test_approves_balanced_ledger_tb_and_traceable_adjustment(self) -> None:
        scorecard = self.auditor.execute_audit(
            self.valid_ai_output(),
            self.ground_truth,
        )

        self.assertEqual(scorecard["data_quality_status"], "APPROVED")
        self.assertEqual(scorecard["rigor_score"], 5.0)
        self.assertTrue(scorecard["is_balanced"])
        self.assertEqual(scorecard["variance_delta"], 0.0)
        self.assertEqual(scorecard["unreconciled_accounts"], [])
        self.assertEqual(
            scorecard["adjustment_traceability_status"],
            "TRACEABLE",
        )

    def test_rejects_trial_balance_variance(self) -> None:
        truth = copy.deepcopy(self.ground_truth)
        truth["trial_balance"][0]["debit"] = "999.50"

        scorecard = self.auditor.execute_audit(self.valid_ai_output(), truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertFalse(scorecard["is_balanced"])
        self.assertIn("ALPHA_US|1000_CASH", scorecard["unreconciled_accounts"])
        self.assertGreater(scorecard["variance_delta"], 0.0)

    def test_rejects_unbalanced_adjustment(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["proposed_adjustments"][0]["entries"][1]["credit"] = "9.00"

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertEqual(
            scorecard["adjustment_traceability_status"],
            "FAILED",
        )
        self.assertIn("ADJ-001", scorecard["failed_adjustments"])

    def test_rejects_adjustment_without_source_row_traceability(self) -> None:
        ai_output = self.valid_ai_output()
        ai_output["proposed_adjustments"][0]["entries"][0]["source_row_ids"] = [
            "MISSING"
        ]

        scorecard = self.auditor.execute_audit(ai_output, self.ground_truth)

        self.assertEqual(scorecard["data_quality_status"], "REJECTED")
        self.assertIn("ADJ-001", scorecard["failed_adjustments"])

    def test_rejects_ai_claim_that_masks_unreconciled_accounts(self) -> None:
        truth = copy.deepcopy(self.ground_truth)
        truth["trial_balance"][0]["debit"] = "999.50"
        ai_output = self.valid_ai_output()
        ai_output["ai_reconciliation"]["is_balanced"] = True
        ai_output["ai_reconciliation"]["unreconciled_accounts"] = []

        scorecard = self.auditor.execute_audit(ai_output, truth)

        self.assertFalse(scorecard["ai_reconciliation_claim_consistent"])
        self.assertEqual(scorecard["data_quality_status"], "REJECTED")

    def test_fails_closed_on_mixed_currency_period_and_unknown_account(self) -> None:
        mixed_currency = copy.deepcopy(self.ground_truth)
        mixed_currency["ledger_rows"][0]["currency"] = "HKD"
        with self.assertRaisesRegex(ValueError, "currency"):
            self.auditor.execute_audit(self.valid_ai_output(), mixed_currency)

        mixed_period = copy.deepcopy(self.ground_truth)
        mixed_period["trial_balance"][0]["period_end"] = "2026-04-30"
        with self.assertRaisesRegex(ValueError, "period_end"):
            self.auditor.execute_audit(self.valid_ai_output(), mixed_period)

        unknown_account = copy.deepcopy(self.ground_truth)
        unknown_account["ledger_rows"][0]["account"] = "9999_UNKNOWN"
        with self.assertRaisesRegex(ValueError, "account_mapping"):
            self.auditor.execute_audit(self.valid_ai_output(), unknown_account)

    def test_requires_source_and_valid_period(self) -> None:
        missing_source = dict(self.ground_truth)
        missing_source.pop("source_id")
        with self.assertRaisesRegex(ValueError, "source_id"):
            self.auditor.execute_audit(self.valid_ai_output(), missing_source)

        invalid_period = dict(self.ground_truth)
        invalid_period["period_end"] = "2026-Q1"
        with self.assertRaisesRegex(ValueError, "period_end"):
            self.auditor.execute_audit(self.valid_ai_output(), invalid_period)

    def test_inputs_are_not_mutated(self) -> None:
        ai_output = self.valid_ai_output()
        ground_truth = copy.deepcopy(self.ground_truth)
        original_ai = copy.deepcopy(ai_output)
        original_truth = copy.deepcopy(ground_truth)

        self.auditor.execute_audit(ai_output, ground_truth)

        self.assertEqual(ai_output, original_ai)
        self.assertEqual(ground_truth, original_truth)


class FinancialReconciliationAuditorIntegrationTests(unittest.TestCase):
    def test_manifest_registers_foas_as_implemented(self) -> None:
        from src.module_manifest import get_module_spec

        specification = get_module_spec(8)
        self.assertEqual(specification.status, "IMPLEMENTED")
        self.assertEqual(specification.class_name, "FinancialReconciliationAuditor")
        self.assertTrue(specification.implementation_path.endswith("foas_auditor.py"))

    def test_foas_runs_as_standalone_json_cli(self) -> None:
        auditor_tests = FinancialReconciliationAuditorTests()
        auditor_tests.setUp()
        ai_output = auditor_tests.valid_ai_output()
        ground_truth = auditor_tests.ground_truth

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            ai_path = temporary / "ai_output.json"
            truth_path = temporary / "ground_truth.json"
            ai_path.write_text(json.dumps(ai_output), encoding="utf-8")
            truth_path.write_text(json.dumps(ground_truth), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(
                        ROOT
                        / "evaluation_kernels"
                        / "layer_3_compliance"
                        / "Module_08_FOAS"
                        / "foas_auditor.py"
                    ),
                    "--ai-output",
                    str(ai_path),
                    "--ground-truth",
                    str(truth_path),
                ],
                cwd=ROOT.parent,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        scorecard = json.loads(result.stdout)
        self.assertEqual(scorecard["data_quality_status"], "APPROVED")


if __name__ == "__main__":
    unittest.main()
