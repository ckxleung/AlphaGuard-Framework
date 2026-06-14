import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation_kernels.layer_3_compliance.Module_01_FRTE.frte_auditor import FilingRiskDeltaAuditor

class FrteAuditorTests(unittest.TestCase):
    def test_approve(self):
        auditor = FilingRiskDeltaAuditor()
        ai = {"ai_summary": "test", "claimed_risk_deltas": [{"topic": "test"}]}
        gt = {
            "prior_period_filing_text": "a", "current_period_filing_text": "b",
            "section_boundaries": ["a"], "source_ids": ["a"],
            "period_end_dates": ["1", "2"], "actual_material_deltas": [{"topic": "test"}],
            "are_filings_comparable": True
        }
        res = auditor.execute_audit(ai, gt)
        self.assertEqual(res["data_quality_status"], "APPROVED")
