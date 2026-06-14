import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation_kernels.layer_3_compliance.Module_16_AMWE.amwe_auditor import AppliedMLWorkflowAuditor

class AmweAuditorTests(unittest.TestCase):
    def test_approve(self):
        auditor = AppliedMLWorkflowAuditor()
        ai = {}
        gt = {}
        res = auditor.execute_audit(ai, gt)
        self.assertEqual(res["data_quality_status"], "APPROVED")
