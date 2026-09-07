import unittest
from services.controls_catalog import calc_compliance, calc_tcvn_compliance

class TestComplianceScore(unittest.TestCase):
    def test_iso27001_compliance_clamped(self):
        # 93 controls in ISO 27001
        res = calc_compliance([], "iso27001")
        self.assertEqual(res['score'], 0)
        self.assertEqual(res['percentage'], 0.0)

        # Normal case
        res = calc_compliance(['A.5.1', 'A.5.2'], "iso27001")
        self.assertEqual(res['score'], 2)
        self.assertLessEqual(res['percentage'], 100.0)

        # Case with duplicate IDs and irrelevant / invalid controls
        bloated_ids = ['A.5.1', 'A.5.1', 'INVALID_CONTROL', 'FAKE.1.2.3'] + [f'A.5.{i}' for i in range(1, 40)]
        res = calc_compliance(bloated_ids, "iso27001")
        self.assertLessEqual(res['score'], 93)
        self.assertLessEqual(res['percentage'], 100.0)
        self.assertGreaterEqual(res['percentage'], 0.0)

    def test_tcvn11930_compliance_clamped(self):
        # 34 controls in TCVN 11930 (NW.*, SV.*, APP.*, DAT.*, MNG.*)
        res = calc_tcvn_compliance([])
        self.assertEqual(res['score'], 0)
        self.assertEqual(res['percentage'], 0.0)

        # Normal case
        res = calc_tcvn_compliance(['NW.01', 'SV.01'])
        self.assertEqual(res['score'], 2)
        self.assertLessEqual(res['percentage'], 100.0)

        # Extreme case: 150 IDs from mixed standards (ISO controls mixed in)
        mixed_ids = [f'A.5.{i}' for i in range(1, 100)] + ['NW.01', 'NW.01', 'SV.01']
        res = calc_tcvn_compliance(mixed_ids)
        # Should only count valid TCVN controls (NW.01, SV.01 = 2 controls)
        self.assertEqual(res['score'], 2)
        self.assertLessEqual(res['score'], 34)
        self.assertLessEqual(res['percentage'], 100.0)

if __name__ == '__main__':
    unittest.main()
