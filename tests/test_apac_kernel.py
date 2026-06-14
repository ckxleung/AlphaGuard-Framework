import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation_kernels.layer_2_valuation.Module_02_APAC.apac_auditor import ApacContagionAuditor

class ApacAuditorTests(unittest.TestCase):
    def test_approve(self):
        auditor = ApacContagionAuditor()
        ai = {}
        gt = {"dated_operating_metrics": {"a":1}, "option_chain_snapshot": {"a":1}}
        res = auditor.execute_audit(ai, gt)
        self.assertEqual(res["data_quality_status"], "APPROVED")
