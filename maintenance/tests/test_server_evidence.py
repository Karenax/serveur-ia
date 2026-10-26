"""Failed or truncated suites must never be silently promoted to passing evidence."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server_evidence import evidence


class ServerEvidenceTests(unittest.TestCase):
    def test_every_initial_failure_requires_a_successful_named_rerun(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)/'base.txt';rerun=Path(folder)/'rerun.txt'
            base.write_text('FAIL: test_a (tests.C.test_a)\nRan 10 tests in 3.0s\nFAILED (failures=1)\n')
            rerun.write_text('test_b (tests.C.test_b) ... ok\nRan 1 test in 1.0s\nOK\n')
            self.assertFalse(evidence(base,[rerun])['passed'])
            rerun.write_text('test_a (tests.C.test_a) ... ok\nRan 1 test in 1.0s\nOK\n')
            report=evidence(base,[rerun])
            self.assertTrue(report['passed']);self.assertFalse(report['base_passed'])
            self.assertEqual(report['initial_failures'],['tests.C.test_a'])

    def test_crash_or_missing_failure_summary_is_not_a_complete_suite(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'base.txt'
            for value in ('test_a ... ok\n','Ran 10 tests in 3.0s\nFAILED (failures=1)\n'):
                path.write_text(value)
                self.assertFalse(evidence(path)['passed'])


if __name__=='__main__':unittest.main()
