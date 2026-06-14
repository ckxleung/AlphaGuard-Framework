import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation_kernels.layer_3_compliance.Module_17_ERCA.erca_auditor import EnterpriseRiskComplianceAuditor

class ErcaAuditorTests(unittest.TestCase):
    def test_approve(self):
        auditor = EnterpriseRiskComplianceAuditor()
        ai = {}
        gt = {}
        res = auditor.execute_audit(ai, gt)
        self.assertEqual(res["data_quality_status"], "APPROVED")
