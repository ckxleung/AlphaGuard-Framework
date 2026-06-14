import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation_kernels.layer_4_strategy.Module_04_CASS.cass_auditor import StrategyConflictAuditor

class CassAuditorTests(unittest.TestCase):
    def test_approve(self):
        auditor = StrategyConflictAuditor()
        ai = {}
        gt = {}
        res = auditor.execute_audit(ai, gt)
        self.assertEqual(res["data_quality_status"], "APPROVED")
