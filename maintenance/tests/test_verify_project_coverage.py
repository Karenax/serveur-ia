"""A passing subset must not be presented as qualification of every platform."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_project import DESKTOP_AUDIT_CHECKS, coverage, definitions


class DesktopAuditCoverageTests(unittest.TestCase):
    def test_subset_reports_unrecorded_checks_and_native_qualification_limit(self):
        checks = {'desktop-server': [], 'desktop-portal': [], 'android': []}
        report = coverage(checks, [{'check': 'desktop-server', 'passed': True}])
        self.assertEqual(report['recorded_checks'], ['desktop-server'])
        self.assertEqual(report['not_recorded_checks'], ['android', 'desktop-portal'])
        self.assertTrue(report['dimensions']['serveur']['recorded_commands_passed'])
        self.assertIsNone(report['dimensions']['android']['recorded_commands_passed'])
        self.assertIn('not established', report['native_windows_qualification'])
        self.assertIn('not established', report['native_linux_qualification'])

    def test_failure_in_one_recorded_command_is_not_hidden(self):
        report = coverage({'desktop-portal': []}, [
            {'check': 'desktop-portal', 'passed': True},
            {'check': 'desktop-portal', 'passed': False},
        ])
        self.assertFalse(report['dimensions']['portail']['recorded_commands_passed'])

    def test_desktop_profile_uses_only_explicit_desktop_browser_scenarios(self):
        checks = definitions(Path('D:/fixture'))
        self.assertEqual(set(DESKTOP_AUDIT_CHECKS), {
            'desktop-server', 'desktop-portal', 'desktop-windows-browser', 'desktop-linux-browser',
        })
        for platform in ('windows', 'linux'):
            commands = checks[f'desktop-{platform}-browser']
            self.assertEqual(len(commands), 1)
            self.assertIn('--desktop-audit', commands[0])
            self.assertIn(f'--{platform}-only', commands[0])


if __name__ == '__main__':
    unittest.main()
