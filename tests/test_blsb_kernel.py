import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation_kernels.layer_4_strategy.Module_07_BLSB.blsb_auditor import StrategyGroundingAuditor

class BlsbAuditorTests(unittest.TestCase):
    def test_approve(self):
        auditor = StrategyGroundingAuditor()
        ai = {}
        gt = {}
        res = auditor.execute_audit(ai, gt)
        self.assertEqual(res["data_quality_status"], "APPROVED")
