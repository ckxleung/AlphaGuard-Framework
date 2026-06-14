import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation_kernels.layer_4_strategy.Module_03_AMDG.amdg_auditor import InstitutionalDeliverableAuditor

class AmdgAuditorTests(unittest.TestCase):
    def test_approve(self):
        auditor = InstitutionalDeliverableAuditor()
        ai = {}
        gt = {}
        res = auditor.execute_audit(ai, gt)
        self.assertEqual(res["data_quality_status"], "APPROVED")
